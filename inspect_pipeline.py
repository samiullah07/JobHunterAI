import inspect
import importlib

checks = [
    ("discover", "jobhunter.workers.discovery", "discover_jobs_scheduled"),
    ("generate", "jobhunter.workers.generation", "generate_for_top_matches"),
    ("queue", "jobhunter.workers.queueing", "queue_applications_for_review"),
]

for label, module_path, func_name in checks:
    try:
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        sig = inspect.signature(func)
        is_async = inspect.iscoroutinefunction(func)
        print(f"{label}: {func_name}{sig} [async={is_async}]")
    except Exception as e:
        print(f"{label}: ERROR - {e}")

# Also check: does the home page exist?
from pathlib import Path
home = Path("frontend/app.py")
print(f"\nHome page exists: {home.exists()}")
print(f"Home page lines: {len(home.read_text(encoding='utf-8').splitlines()) if home.exists() else 0}")
