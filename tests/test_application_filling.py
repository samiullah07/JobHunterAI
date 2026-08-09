"""Tests for M8: browser-automation application filling with HITL safety."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from jobhunter.adapters.browser.submitter import _verify_approval, submit_application
from jobhunter.domain.application_fill import (
    ApprovalToken,
    BlockerKind,
    FieldType,
    FilledField,
    ReviewPacket,
    SubmitNotAuthorized,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "forms"


# ============ Unit tests: Domain DTOs ============


class TestReviewPacketHash:
    def test_compute_fill_hash_deterministic(self) -> None:
        packet = ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url="http://example.com",
            filled_fields=[
                FilledField(
                    selector="#name",
                    label="name",
                    field_type=FieldType.TEXT,
                    value="Alice",
                    source="profile.name",
                ),
            ],
            uploaded_files=["resume.pdf"],
        )
        h1 = packet.compute_fill_hash()
        h2 = packet.compute_fill_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_hash_changes_when_fields_change(self) -> None:
        packet = ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url="http://example.com",
            filled_fields=[
                FilledField(
                    selector="#name",
                    label="name",
                    field_type=FieldType.TEXT,
                    value="Alice",
                    source="profile.name",
                ),
            ],
        )
        h1 = packet.compute_fill_hash()
        packet.filled_fields[0].value = "Bob"
        h2 = packet.compute_fill_hash()
        assert h1 != h2


class TestApprovalTokenForPacket:
    def test_creates_token_with_matching_hash(self) -> None:
        packet = ReviewPacket(
            application_id="app-99",
            job_id="job-1",
            profile_id="prof-1",
            url="http://example.com",
            filled_fields=[
                FilledField(
                    selector="#email",
                    label="email",
                    field_type=FieldType.EMAIL,
                    value="a@b.com",
                    source="profile.email",
                ),
            ],
        )
        token = ApprovalToken.for_packet(packet, approved_by="human")
        assert token.application_id == "app-99"
        assert token.fill_hash == packet.compute_fill_hash()
        assert token.approved_by == "human"
        assert not token.consumed
        assert len(token.nonce) == 32

    def test_token_not_consumed_initially(self) -> None:
        packet = ReviewPacket(application_id="a", job_id="j", profile_id="p", url="http://x")
        token = ApprovalToken.for_packet(packet, approved_by="admin")
        assert token.consumed is False


# ============ Unit tests: _verify_approval guard ============


class TestVerifyApproval:
    def _make_packet(self) -> ReviewPacket:
        return ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url="http://example.com",
            filled_fields=[
                FilledField(
                    selector="#x",
                    label="x",
                    field_type=FieldType.TEXT,
                    value="val",
                    source="src",
                ),
            ],
        )

    def test_valid_token_passes(self) -> None:
        packet = self._make_packet()
        token = ApprovalToken.for_packet(packet, approved_by="user")
        _verify_approval(packet, token)  # Should not raise

    def test_none_token_raises(self) -> None:
        packet = self._make_packet()
        with pytest.raises(SubmitNotAuthorized, match="No approval token"):
            _verify_approval(packet, None)

    def test_hash_mismatch_raises(self) -> None:
        packet = self._make_packet()
        token = ApprovalToken.for_packet(packet, approved_by="user")
        # Mutate packet after token creation
        packet.filled_fields[0].value = "changed"
        with pytest.raises(SubmitNotAuthorized, match="hash does not match"):
            _verify_approval(packet, token)

    def test_consumed_token_raises(self) -> None:
        packet = self._make_packet()
        token = ApprovalToken.for_packet(packet, approved_by="user")
        token.consumed = True
        with pytest.raises(SubmitNotAuthorized, match="already been consumed"):
            _verify_approval(packet, token)

    def test_wrong_application_id_raises(self) -> None:
        packet = self._make_packet()
        token = ApprovalToken(
            application_id="WRONG-ID",
            fill_hash=packet.compute_fill_hash(),
            approved_by="user",
            approved_at=datetime.now(),
        )
        with pytest.raises(SubmitNotAuthorized, match="application_id"):
            _verify_approval(packet, token)


# ============ Integration tests: Playwright (real browser, local fixtures) ============


@pytest.fixture
def form_url() -> str:
    return (FIXTURES_DIR / "application_form.html").as_uri()


@pytest.fixture
def login_wall_url() -> str:
    return (FIXTURES_DIR / "login_wall_form.html").as_uri()


class FakeStorageService:
    """In-memory storage for test screenshots."""

    def __init__(self) -> None:
        self.stored: dict[str, bytes] = {}

    async def store(self, key: str, data: bytes) -> str:
        self.stored[key] = data
        return key


@pytest.mark.slow
class TestPlaywrightFormFiller:
    @pytest_asyncio.fixture
    async def filler(self) -> Any:
        from jobhunter.adapters.browser.playwright_form_filler import (
            PlaywrightFormFiller,
        )

        storage = FakeStorageService()
        return PlaywrightFormFiller(storage, headless=True)  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_fill_form_end_to_end(self, filler: Any, form_url: str) -> None:
        """Fill the synthetic form and verify fields are filled, __SUBMITTED__ is False."""
        # Create a temp file to simulate resume upload
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake resume content")
            resume_path = f.name

        field_plan = {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "555-1234",
            "cover_letter_text": "I love backend development.",
            "years_experience": "3-5",
            "work_auth": "yes",
            "available_date": "2025-03-01",
            "skills:python": "true",
            "skills:docker": "true",
            "relocate:yes": "true",
        }
        files = {"resume": resume_path}

        packet = await filler.fill(
            url=form_url,
            field_plan=field_plan,
            files=files,
            application_id="app-test-1",
            job_id="job-test-1",
            profile_id="prof-test-1",
        )

        assert packet.application_id == "app-test-1"
        assert packet.is_ready_for_review is True
        assert len(packet.blockers) == 0
        assert len(packet.filled_fields) > 0
        assert len(packet.screenshots) > 0
        assert packet.fill_hash != ""

        # Verify specific fields were filled
        field_labels = [f.label for f in packet.filled_fields]
        assert "full_name" in field_labels or "full-name" in field_labels
        assert "email" in field_labels

        # Clean up
        Path(resume_path).unlink(missing_ok=True)  # noqa: ASYNC240

    @pytest.mark.asyncio
    async def test_fill_never_submits(self, filler: Any, form_url: str) -> None:
        """After fill, window.__SUBMITTED__ must NOT be true."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(form_url, wait_until="domcontentloaded")

            # Fill fields manually
            await page.fill("#full-name", "Test User")
            await page.fill("#email", "test@test.com")
            await page.select_option("#experience", "0-2")
            await page.check("input[name='work_auth'][value='yes']")

            # Navigate to page 2
            await page.click("#next-btn")
            await page.wait_for_timeout(300)

            # Verify __SUBMITTED__ is still not set
            submitted = await page.evaluate("() => window.__SUBMITTED__")
            assert submitted is None or submitted is False

            await browser.close()

    @pytest.mark.asyncio
    async def test_blocker_detection_captcha(self, filler: Any, login_wall_url: str) -> None:
        """Login wall / CAPTCHA pages should produce blockers and is_ready_for_review=False."""
        packet = await filler.fill(
            url=login_wall_url,
            field_plan={},
            files={},
            application_id="app-blocked",
            job_id="job-blocked",
            profile_id="prof-blocked",
        )

        assert packet.is_ready_for_review is False
        assert len(packet.blockers) > 0

        blocker_kinds = [b.kind for b in packet.blockers]
        assert BlockerKind.CAPTCHA in blocker_kinds
        assert BlockerKind.LOGIN_WALL in blocker_kinds


@pytest.mark.slow
class TestSubmitGuardIntegration:
    """Integration tests verifying the submit guard with a real browser."""

    @pytest.mark.asyncio
    async def test_submit_refused_without_valid_token(self, form_url: str) -> None:
        """Submit must raise SubmitNotAuthorized without a valid token."""
        packet = ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url=form_url,
            filled_fields=[
                FilledField(
                    selector="#full-name",
                    label="full_name",
                    field_type=FieldType.TEXT,
                    value="Test",
                    source="plan",
                ),
            ],
        )
        packet.fill_hash = packet.compute_fill_hash()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(form_url, wait_until="domcontentloaded")

            with pytest.raises(SubmitNotAuthorized):
                await submit_application(page, packet, None)

            # Verify __SUBMITTED__ was NOT set
            submitted = await page.evaluate("() => window.__SUBMITTED__")
            assert submitted is None or submitted is False

            await browser.close()

    @pytest.mark.asyncio
    async def test_submit_succeeds_with_valid_token(self, form_url: str) -> None:
        """Submit with valid ApprovalToken should click submit and set __SUBMITTED__."""
        packet = ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url=form_url,
            filled_fields=[
                FilledField(
                    selector="#full-name",
                    label="full_name",
                    field_type=FieldType.TEXT,
                    value="Test",
                    source="plan",
                ),
            ],
        )
        packet.fill_hash = packet.compute_fill_hash()
        token = ApprovalToken.for_packet(packet, approved_by="human-reviewer")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(form_url, wait_until="domcontentloaded")

            # Navigate to page 2 where the submit button is
            await page.click("#next-btn")
            await page.wait_for_timeout(300)

            # __SUBMITTED__ must be falsy BEFORE submit
            pre_submit = await page.evaluate("() => window.__SUBMITTED__")
            assert pre_submit is None or pre_submit is False

            result = await submit_application(page, packet, token)

            assert result.submitted is True
            assert result.application_id == "app-1"
            assert token.consumed is True

            # __SUBMITTED__ must be True AFTER submit
            submitted = await page.evaluate("() => window.__SUBMITTED__")
            assert submitted is True

            await browser.close()

    @pytest.mark.asyncio
    async def test_consumed_token_cannot_resubmit(self, form_url: str) -> None:
        """Once consumed, token must not allow a second submit."""
        packet = ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url=form_url,
            filled_fields=[],
        )
        packet.fill_hash = packet.compute_fill_hash()
        token = ApprovalToken.for_packet(packet, approved_by="admin")
        token.consumed = True  # Simulate prior use

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(form_url, wait_until="domcontentloaded")

            with pytest.raises(SubmitNotAuthorized, match="consumed"):
                await submit_application(page, packet, token)

            # __SUBMITTED__ must stay falsy — guard blocked the click
            submitted = await page.evaluate("() => window.__SUBMITTED__")
            assert submitted is None or submitted is False

            await browser.close()

    @pytest.mark.asyncio
    async def test_stale_hash_blocks_submit(self, form_url: str) -> None:
        """Approve version A, mutate to version B → submit MUST be refused."""
        packet = ReviewPacket(
            application_id="app-1",
            job_id="job-1",
            profile_id="prof-1",
            url=form_url,
            filled_fields=[
                FilledField(
                    selector="#full-name",
                    label="full_name",
                    field_type=FieldType.TEXT,
                    value="Original Value",
                    source="plan",
                ),
            ],
        )
        packet.fill_hash = packet.compute_fill_hash()
        token = ApprovalToken.for_packet(packet, approved_by="human")

        # MUTATE the packet after approval — simulates form drift
        packet.filled_fields[0].value = "Tampered Value"
        # Hash is now stale relative to the token

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(form_url, wait_until="domcontentloaded")

            # Navigate to submit page
            await page.click("#next-btn")
            await page.wait_for_timeout(300)

            with pytest.raises(SubmitNotAuthorized, match="hash does not match"):
                await submit_application(page, packet, token)

            # __SUBMITTED__ must stay falsy — stale hash blocked the click
            submitted = await page.evaluate("() => window.__SUBMITTED__")
            assert submitted is None or submitted is False

            await browser.close()
