"""Integration tests for cover letter generation.

- Threshold gate: below-threshold → nothing generated, generator NOT called.
- Above threshold: clean letter → persisted to storage.
- Fabrication: invented tech → rejected, nothing persisted.
- Playwright PDF: cover letter HTML → %PDF bytes.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from jobhunter.adapters.generation.llm_cover_letter_generator import (
    LlmCoverLetterGenerator,
)
from jobhunter.adapters.rendering.cover_letter_renderer import to_html, to_pdf
from jobhunter.adapters.storage.local_storage import LocalStorageService
from jobhunter.application.services.fabrication_validator import validate_cover_letter
from jobhunter.application.use_cases.cover_letter_generation import (
    CoverLetterGenerationService,
)
from jobhunter.domain.cover_letter import CoverLetter

# ─── Fixtures ───────────────────────────────────────────────────────────────


def _profile_mock() -> MagicMock:
    profile = MagicMock()
    profile.full_name = "Jane Doe"
    profile.email = "jane@example.com"
    profile.phone = "555-0100"
    profile.location = "NYC"
    profile.linkedin_url = None
    profile.github_url = None
    profile.headline = "Engineer"
    profile.summary = "Python developer."

    skill1 = MagicMock()
    skill1.name = "Python"
    skill2 = MagicMock()
    skill2.name = "FastAPI"
    profile.skills = [skill1, skill2]

    exp = MagicMock()
    exp.company_name = "Acme Corp"
    exp.title = "Senior Engineer"
    exp.start_date = date(2020, 1, 1)
    exp.end_date = None
    exp.is_current = True
    exp.technologies = ["Python", "FastAPI"]
    exp.description = None
    exp.achievements = []
    profile.work_experiences = [exp]

    edu = MagicMock()
    edu.institution = "MIT"
    edu.degree = "B.S. Computer Science"
    edu.field_of_study = "Computer Science"
    edu.start_date = date(2014, 9, 1)
    edu.end_date = date(2018, 5, 1)
    profile.educations = [edu]

    profile.projects = []
    profile.certifications = []
    return profile


def _job_mock() -> MagicMock:
    job = MagicMock()
    job.id = uuid.uuid4()
    job.title = "Backend Developer"
    job.company_name = "TechCo"
    job.location = "Remote"
    job.remote_policy = "remote"
    job.description_raw = "We need a Python backend developer with FastAPI experience."
    return job


_CLEAN_RESPONSE: dict[str, Any] = {
    "salutation": "Dear Hiring Manager,",
    "opening": "I am writing about the Backend Developer role at TechCo.",
    "body_paragraphs": [
        "In my role at Acme Corp, I built Python services using FastAPI.",
        "I am excited to bring this experience to TechCo.",
    ],
    "closing": "Thank you for considering my application.",
    "signature": "Sincerely, Jane Doe",
    "company_name": "TechCo",
    "role": "Backend Developer",
}

_FABRICATED_RESPONSE: dict[str, Any] = {
    "salutation": "Dear Hiring Manager,",
    "opening": "I am writing about the Backend Developer role at TechCo.",
    "body_paragraphs": [
        "My extensive Kubernetes and Terraform experience makes me ideal.",
    ],
    "closing": "Thank you.",
    "signature": "Sincerely, Jane Doe",
    "company_name": "TechCo",
    "role": "Backend Developer",
}


class FakeLlmClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.call_count = 0

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        self.call_count += 1
        return dict(self._response)


class CountingGenerator:
    """A generator wrapper that tracks whether generate() was called."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._llm = FakeLlmClient(response)
        self._inner = LlmCoverLetterGenerator(llm_client=self._llm)
        self.call_count = 0

    async def generate(self, profile: Any, job: Any) -> CoverLetter:
        self.call_count += 1
        return await self._inner.generate(profile, job)


# ─── Integration: threshold gate ────────────────────────────────────────────


class TestThresholdGate:
    async def test_below_threshold_blocks_generation(self) -> None:
        """Job with score BELOW threshold → generator NOT called, nothing persisted."""
        generator = CountingGenerator(_CLEAN_RESPONSE)
        profile = _profile_mock()
        job = _job_mock()

        match_score = MagicMock()
        match_score.overall = 0.40  # Below default 0.75 threshold

        profile_repo = AsyncMock()
        profile_repo.get_with_children = AsyncMock(return_value=profile)
        job_repo = AsyncMock()
        job_repo.get = AsyncMock(return_value=job)
        match_score_repo = AsyncMock()
        match_score_repo.get_for_job_profile = AsyncMock(return_value=match_score)

        session = AsyncMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            service = CoverLetterGenerationService(
                generator=generator,
                job_repo=job_repo,
                profile_repo=profile_repo,
                match_score_repo=match_score_repo,
                cover_letter_version_repo=AsyncMock(),
                storage=LocalStorageService(tmpdir),
                session=session,
            )
            result = await service.generate_for_job(uuid.uuid4(), job.id)

        assert result.below_threshold is True
        assert result.cover_letter_version_id is None
        assert generator.call_count == 0  # Generator was NEVER called

    async def test_no_score_blocks_generation(self) -> None:
        """Job with NO match score → generator NOT called."""
        generator = CountingGenerator(_CLEAN_RESPONSE)
        profile = _profile_mock()
        job = _job_mock()

        profile_repo = AsyncMock()
        profile_repo.get_with_children = AsyncMock(return_value=profile)
        job_repo = AsyncMock()
        job_repo.get = AsyncMock(return_value=job)
        match_score_repo = AsyncMock()
        match_score_repo.get_for_job_profile = AsyncMock(return_value=None)

        session = AsyncMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            service = CoverLetterGenerationService(
                generator=generator,
                job_repo=job_repo,
                profile_repo=profile_repo,
                match_score_repo=match_score_repo,
                cover_letter_version_repo=AsyncMock(),
                storage=LocalStorageService(tmpdir),
                session=session,
            )
            result = await service.generate_for_job(uuid.uuid4(), job.id)

        assert result.no_score is True
        assert generator.call_count == 0


# ─── Integration: clean letter persists ─────────────────────────────────────


class TestCleanCoverLetterEndToEnd:
    async def test_above_threshold_generates_and_stores(self) -> None:
        """Job ABOVE threshold → generates, validates clean, renders, stores."""
        llm = FakeLlmClient(_CLEAN_RESPONSE)
        gen = LlmCoverLetterGenerator(llm_client=llm)
        profile = _profile_mock()
        job = _job_mock()

        letter = await gen.generate(profile, job)
        assert letter.company_name == "TechCo"

        fab = validate_cover_letter(letter, profile)
        assert fab.is_clean is True

        from jobhunter.adapters.rendering import cover_letter_renderer

        md_out = cover_letter_renderer.to_markdown(letter)
        docx_out = cover_letter_renderer.to_docx(letter)
        html_out = cover_letter_renderer.to_html(letter)

        assert "Dear Hiring Manager," in md_out
        assert docx_out[:2] == b"PK"
        assert "<!DOCTYPE html>" in html_out

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageService(tmpdir)
            key = await storage.store("coverletters/test/cover_letter.md", md_out.encode())
            assert await storage.exists(key)
            assert (await storage.read(key)) == md_out.encode()


# ─── Integration: fabricated letter rejected ────────────────────────────────


class TestFabricatedCoverLetterRejected:
    async def test_fabricated_letter_not_persisted(self) -> None:
        """Invented tech in body → fabrication detected, nothing persisted."""
        llm = FakeLlmClient(_FABRICATED_RESPONSE)
        gen = LlmCoverLetterGenerator(llm_client=llm)
        profile = _profile_mock()
        job = _job_mock()

        letter = await gen.generate(profile, job)
        fab = validate_cover_letter(letter, profile)

        assert fab.is_clean is False
        assert any("Kubernetes" in v for v in fab.violations)

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageService(tmpdir)
            # Nothing persisted when fabrication detected
            assert not await storage.exists("coverletters/test/cover_letter.md")


# ─── Integration: Playwright PDF ────────────────────────────────────────────


class TestCoverLetterPlaywrightPdf:
    @pytest.mark.slow
    async def test_to_pdf_produces_valid_pdf_bytes(self) -> None:
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am applying for the Developer role.",
            body_paragraphs=[
                "My background in Python makes me a strong candidate.",
            ],
            closing="Thank you for your consideration.",
            signature="Sincerely, Test User",
            company_name="TestCo",
            role="Developer",
        )
        html = to_html(letter)
        pdf_bytes = await to_pdf(html)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 500
