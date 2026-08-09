"""Tests for M9: human-in-the-loop review UI and approval-token minting."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from jobhunter.domain.application_fill import (
    ApprovalToken,
    Blocker,
    BlockerKind,
    FieldType,
    FilledField,
    ReviewPacket,
)
from jobhunter.domain.enums import ApplicationStatus
from jobhunter.domain.resume import FabricationReport
from jobhunter.domain.review import (
    ApplicationReviewView,
    ReviewDecision,
    ReviewOutcome,
    ReviewRefused,
)

# ============ Unit tests: ReviewService.record_decision ============


def _make_fake_app(
    status: str = ApplicationStatus.READY_FOR_REVIEW,
    has_answers: bool = False,
) -> MagicMock:
    """Create a fake Application ORM object for testing."""
    app = MagicMock()
    app.id = uuid.uuid4()
    app.job_id = uuid.uuid4()
    app.profile_id = uuid.uuid4()
    app.status = status
    app.notes = ""
    app.answers = []
    app.screenshots = []
    if has_answers:
        ans = MagicMock()
        ans.question = "Name"
        ans.value = "Jane"
        ans.source = "profile"
        app.answers = [ans]
    return app


class TestRecordDecisionApprove:
    """APPROVE mints a token bound to fill_hash and does NOT submit."""

    @pytest.mark.asyncio
    async def test_approve_mints_token_with_correct_fill_hash(self) -> None:
        """Token's fill_hash must equal the packet's compute_fill_hash()."""
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        outcome = await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.APPROVE,
            approved_by="test-human",
        )

        assert outcome.decision == ReviewDecision.APPROVE
        assert outcome.token is not None
        assert outcome.token.application_id == str(fake_app.id)
        assert outcome.token.approved_by == "test-human"
        assert not outcome.token.consumed

        # Verify the hash matches a fresh packet computation
        from jobhunter.application.use_cases.review import _build_review_packet_from_app

        packet = _build_review_packet_from_app(fake_app)
        assert outcome.token.fill_hash == packet.compute_fill_hash()

    @pytest.mark.asyncio
    async def test_approve_sets_status_to_approved(self) -> None:
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.APPROVE,
            approved_by="human",
        )

        assert fake_app.status == ApplicationStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_does_not_import_or_call_submit(self) -> None:
        """Structurally prove the review service never imports or calls submit_application."""
        import ast
        import inspect

        from jobhunter.application.use_cases import review as review_mod

        source_code = inspect.getsource(review_mod)
        tree = ast.parse(source_code)

        # Walk the AST — look for imports of submitter or calls to submit_application
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "submitter" not in module, f"Review module imports from submitter: {module}"
                for alias in node.names:
                    assert alias.name != "submit_application", (
                        "Review module imports submit_application"
                    )
            if isinstance(node, ast.Call):
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                assert name != "submit_application", "Review module calls submit_application"

    @pytest.mark.asyncio
    async def test_approve_with_blockers_no_override_raises(self) -> None:
        """Blockers present + override=False → ReviewRefused, no token."""
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app(status="not_ready")
        # Make is_ready_for_review False (status != READY_FOR_REVIEW)
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        with pytest.raises(ReviewRefused, match="blockers present"):
            await service.record_decision(
                application_id=str(fake_app.id),
                decision=ReviewDecision.APPROVE,
                approved_by="human",
                override=False,
            )

        # Status should NOT have changed
        assert fake_app.status == "not_ready"

    @pytest.mark.asyncio
    async def test_approve_with_blockers_override_true_mints_token(self) -> None:
        """With override=True, token is minted even if blockers exist."""
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app(status="not_ready")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        outcome = await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.APPROVE,
            approved_by="admin",
            override=True,
        )

        assert outcome.token is not None
        assert outcome.override_used is True
        assert fake_app.status == ApplicationStatus.APPROVED


class TestRecordDecisionOther:
    @pytest.mark.asyncio
    async def test_reject_sets_rejected_status(self) -> None:
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        outcome = await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.REJECT,
            note="Not a good fit",
        )

        assert outcome.decision == ReviewDecision.REJECT
        assert fake_app.status == ApplicationStatus.REJECTED
        assert outcome.token is None

    @pytest.mark.asyncio
    async def test_skip_sets_skipped_status(self) -> None:
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        outcome = await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.SKIP,
        )

        assert outcome.decision == ReviewDecision.SKIP
        assert fake_app.status == ApplicationStatus.SKIPPED
        assert outcome.token is None

    @pytest.mark.asyncio
    async def test_edit_records_intent_keeps_ready(self) -> None:
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        outcome = await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.EDIT,
            note="Fix bullet 3",
        )

        assert outcome.decision == ReviewDecision.EDIT
        assert fake_app.status == ApplicationStatus.READY_FOR_REVIEW
        assert outcome.token is None
        assert "edit" in (fake_app.notes or "").lower()

    @pytest.mark.asyncio
    async def test_regenerate_records_intent(self) -> None:
        from jobhunter.application.use_cases.review import ReviewService

        fake_app = _make_fake_app()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_app
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = ReviewService(session)
        outcome = await service.record_decision(
            application_id=str(fake_app.id),
            decision=ReviewDecision.REGENERATE,
        )

        assert outcome.decision == ReviewDecision.REGENERATE
        assert fake_app.status == ApplicationStatus.READY_FOR_REVIEW
        assert outcome.token is None


# ============ Unit tests: ApplicationReviewView ============


class TestApplicationReviewView:
    def test_has_blocking_issues_with_blockers(self) -> None:
        view = ApplicationReviewView(
            application_id="a",
            job_id="j",
            profile_id="p",
            blockers=[Blocker(kind=BlockerKind.CAPTCHA, detail="reCAPTCHA")],
            is_ready_for_review=True,
        )
        assert view.has_blocking_issues is True

    def test_has_blocking_issues_fabrication_resume(self) -> None:
        view = ApplicationReviewView(
            application_id="a",
            job_id="j",
            profile_id="p",
            fabrication_report_resume=FabricationReport(is_clean=False, violations=["fake"]),
            is_ready_for_review=True,
        )
        assert view.has_blocking_issues is True

    def test_has_blocking_issues_not_ready(self) -> None:
        view = ApplicationReviewView(
            application_id="a",
            job_id="j",
            profile_id="p",
            is_ready_for_review=False,
        )
        assert view.has_blocking_issues is True

    def test_no_blocking_issues_when_clean(self) -> None:
        view = ApplicationReviewView(
            application_id="a",
            job_id="j",
            profile_id="p",
            is_ready_for_review=True,
        )
        assert view.has_blocking_issues is False


# ============ Unit tests: build_review_view assembles correctly ============


class TestBuildReviewView:
    @pytest.mark.asyncio
    async def test_assembles_job_resume_cover_answers(self) -> None:
        """build_review_view populates all fields from seeded data."""
        from jobhunter.application.use_cases.review import ReviewService

        # Build fake objects
        job = MagicMock()
        job.company_name = "Acme Corp"
        job.title = "Senior Engineer"
        job.location = "Remote"
        job.salary_min = 120000
        job.salary_max = 160000
        job.salary_currency = "USD"

        ans = MagicMock()
        ans.question = "Years of experience"
        ans.value = "5"
        ans.source = "profile"

        screenshot = MagicMock()
        screenshot.storage_key = "screenshots/app-1/page1.png"

        app = MagicMock()
        app.id = uuid.uuid4()
        app.job_id = uuid.uuid4()
        app.profile_id = uuid.uuid4()
        app.status = ApplicationStatus.READY_FOR_REVIEW
        app.resume_version_id = uuid.uuid4()
        app.cover_letter_version_id = uuid.uuid4()
        app.job = job
        app.answers = [ans]
        app.screenshots = [screenshot]

        resume = MagicMock()
        resume.id = app.resume_version_id
        resume.canonical_json = {
            "contact": {"name": "Jane", "email": "jane@x.com"},
            "summary": "Engineer with 5 years",
            "experience": [],
            "skills": ["Python", "Go"],
        }
        resume.storage_keys = {}

        cover_letter = MagicMock()
        cover_letter.id = app.cover_letter_version_id
        cover_letter.body_markdown = "Dear Hiring Manager..."

        match_score = MagicMock()
        match_score.overall = 0.87
        match_score.rationale = "Strong skill match"

        # Mock session to return different objects for different queries
        session = AsyncMock()
        call_count = [0]

        async def mock_execute(stmt: Any) -> MagicMock:
            call_count[0] += 1
            result = MagicMock()
            # First call: Application, Second: MatchScore, Third: Resume, Fourth: CoverLetter
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = app
            elif call_count[0] == 2:
                result.scalar_one_or_none.return_value = match_score
            elif call_count[0] == 3:
                result.scalar_one_or_none.return_value = resume
            elif call_count[0] == 4:
                result.scalar_one_or_none.return_value = cover_letter
            else:
                result.scalar_one_or_none.return_value = None
            return result

        session.execute = mock_execute

        service = ReviewService(session)
        view = await service.build_review_view(str(app.id))

        assert view is not None
        assert view.company == "Acme Corp"
        assert view.role == "Senior Engineer"
        assert view.match_score == 0.87
        assert "Jane" in view.resume_preview_markdown
        assert "Dear Hiring Manager" in view.cover_letter_preview_markdown
        assert len(view.filled_fields) == 1
        assert view.filled_fields[0].value == "5"
        assert len(view.screenshot_keys) == 1
        assert view.is_ready_for_review is True


# ============ Streamlit module import safety ============


class TestStreamlitModuleImport:
    def test_review_app_imports_without_running_streamlit(self) -> None:
        """The frontend module must import safely without launching a server."""
        import importlib

        mod = importlib.import_module("frontend.review_app")
        assert hasattr(mod, "main")
        assert hasattr(mod, "render_warnings")
        assert hasattr(mod, "render_job_summary")
        assert hasattr(mod, "render_action_buttons")
        assert hasattr(mod, "render_artifacts")
        assert hasattr(mod, "handle_decision")
        assert callable(mod.main)

    def test_review_app_has_no_submit_dependency(self) -> None:
        """The frontend module must not reference submit_application."""
        import inspect

        import frontend.review_app as mod

        source = inspect.getsource(mod)
        assert "submit_application" not in source


# ============ Domain model: ReviewOutcome ============


class TestReviewOutcome:
    def test_approve_outcome_carries_token(self) -> None:
        packet = ReviewPacket(
            application_id="app-1",
            job_id="j",
            profile_id="p",
            url="http://x",
            filled_fields=[
                FilledField(
                    selector="#x", label="x", field_type=FieldType.TEXT, value="v", source="s"
                )
            ],
        )
        packet.fill_hash = packet.compute_fill_hash()
        token = ApprovalToken.for_packet(packet, approved_by="reviewer")

        outcome = ReviewOutcome(
            application_id="app-1",
            decision=ReviewDecision.APPROVE,
            token=token,
        )
        assert outcome.token is not None
        assert outcome.token.fill_hash == packet.compute_fill_hash()
        assert not outcome.refused

    def test_refused_outcome(self) -> None:
        outcome = ReviewOutcome(
            application_id="app-1",
            decision=ReviewDecision.APPROVE,
            refused=True,
            refusal_reason="Blockers present",
        )
        assert outcome.refused
        assert outcome.token is None
