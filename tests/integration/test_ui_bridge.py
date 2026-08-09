import pytest

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

def test_sync_to_async_bridge_works():
    """Test that the async bridge works correctly in Streamlit context.

    This test mimics what happens in Streamlit:
    - Calls _run_async helper
    - Executes async DB operations through ReviewService
    - Returns successfully without 'send' error
    """
    try:
        from frontend.review_app import _run_async, load_review_queue, load_review_view
        # Execute the async calls synchronously via _run_async
        queue = _run_async(load_review_queue())
        assert isinstance(queue, list), "load_review_queue should return a list"
        assert len(queue) > 0, "Queue should contain seeded application"

        # Get application ID and load full view
        app_id = queue[0]["id"]
        view = _run_async(load_review_view(app_id))
        assert app_id is not None, "Application ID must be valid"
        assert hasattr(view, 'company'), "View should have company attribute"

        print("✓ Async bridge integration test passed")
        print(f"  - Queue loaded with {len(queue)} applications")
        print(f"  - Loaded view for application: {view.company} - {view.role}")

    except Exception as e:
        pytest.fail(f"UI bridge test failed with error: {e}")