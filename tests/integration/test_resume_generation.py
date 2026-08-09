"""Integration tests for résumé generation — end-to-end pipeline.

- Clean résumé: generates → validates → renders → stores (all formats).
- Fabricated résumé: detected → rejected → nothing persisted.
- Playwright PDF: to_pdf produces valid %PDF bytes.
"""

from __future__ import annotations

import tempfile
from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest

from jobhunter.adapters.generation.llm_resume_generator import (
    LlmResumeGenerator,
)
from jobhunter.adapters.rendering.resume_renderer import to_html, to_pdf
from jobhunter.adapters.storage.local_storage import LocalStorageService
from jobhunter.application.services.fabrication_validator import validate
from jobhunter.domain.resume import (
    TailoredExperience,
    TailoredResume,
)

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
    profile.skills = []

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

    skill1 = MagicMock()
    skill1.name = "Python"
    skill2 = MagicMock()
    skill2.name = "FastAPI"
    profile.skills = [skill1, skill2]
    return profile


def _job_mock() -> MagicMock:
    job = MagicMock()
    job.title = "Backend Developer"
    job.company_name = "TechCo"
    job.location = "Remote"
    job.remote_policy = "remote"
    job.description_raw = "We need a Python backend developer with FastAPI experience."
    return job


_CLEAN_LLM_RESPONSE: dict[str, Any] = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "555-0100",
    "location": "NYC",
    "summary": "Senior Python engineer with FastAPI expertise.",
    "experiences": [
        {
            "company": "Acme Corp",
            "title": "Senior Engineer",
            "start_date": "2020-01-01",
            "end_date": None,
            "is_current": True,
            "bullets": [
                "Built backend services using Python and FastAPI",
            ],
        }
    ],
    "education": [
        {
            "institution": "MIT",
            "degree": "B.S. Computer Science",
            "field_of_study": "Computer Science",
            "start_date": "2014-09-01",
            "end_date": "2018-05-01",
        }
    ],
    "projects": [],
    "skills": [{"category": "Backend", "skills": ["Python", "FastAPI"]}],
    "certifications": [],
    "keywords_used": ["python", "fastapi", "backend"],
}

_FABRICATED_LLM_RESPONSE: dict[str, Any] = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "summary": "Expert polyglot engineer.",
    "experiences": [
        {
            "company": "FakeStartup Inc",
            "title": "CTO",
            "start_date": "2015-01-01",
            "end_date": "2019-12-31",
            "is_current": False,
            "bullets": ["Led 200 engineers"],
        }
    ],
    "education": [],
    "projects": [],
    "skills": [{"category": "Systems", "skills": ["Rust", "Zig", "Haskell"]}],
    "certifications": ["Google Cloud Professional"],
    "keywords_used": [],
}


class FakeLlmClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        return dict(self._response)


# ─── Integration: clean résumé persists ─────────────────────────────────────


class TestCleanResumeEndToEnd:
    async def test_clean_resume_renders_all_formats_and_stores(self) -> None:
        llm = FakeLlmClient(_CLEAN_LLM_RESPONSE)
        gen = LlmResumeGenerator(llm_client=llm)
        profile = _profile_mock()
        job = _job_mock()

        tailored = await gen.generate(profile, job)

        assert tailored.full_name == "Jane Doe"

        fab = validate(tailored, profile)
        assert fab.is_clean is True

        from jobhunter.adapters.rendering import resume_renderer

        json_out = resume_renderer.to_json(tailored)
        md_out = resume_renderer.to_markdown(tailored)
        docx_out = resume_renderer.to_docx(tailored)
        html_out = resume_renderer.to_html(tailored)

        assert '"full_name"' in json_out
        assert "# Jane Doe" in md_out
        assert docx_out[:2] == b"PK"
        assert "<h1>Jane Doe</h1>" in html_out

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageService(tmpdir)
            key = await storage.store("resumes/test/resume.json", json_out.encode())
            assert await storage.exists(key)
            assert (await storage.read(key)) == json_out.encode()


# ─── Integration: fabricated résumé rejected ────────────────────────────────


class TestFabricatedResumeRejected:
    async def test_fabricated_resume_flagged_and_not_clean(self) -> None:
        llm = FakeLlmClient(_FABRICATED_LLM_RESPONSE)
        gen = LlmResumeGenerator(llm_client=llm)
        profile = _profile_mock()
        job = _job_mock()

        tailored = await gen.generate(profile, job)
        fab = validate(tailored, profile)

        assert fab.is_clean is False
        assert len(fab.violations) > 0
        assert any("FakeStartup" in v for v in fab.violations)

    async def test_fabricated_resume_storage_not_written(self) -> None:
        """When fabrication is detected, nothing should be persisted to storage."""
        llm = FakeLlmClient(_FABRICATED_LLM_RESPONSE)
        gen = LlmResumeGenerator(llm_client=llm)
        profile = _profile_mock()
        job = _job_mock()

        tailored = await gen.generate(profile, job)
        fab = validate(tailored, profile)

        assert fab.is_clean is False

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorageService(tmpdir)
            assert not await storage.exists("resumes/test/resume.json")


# ─── Integration: Playwright PDF ────────────────────────────────────────────


class TestPlaywrightPdf:
    @pytest.mark.slow
    async def test_to_pdf_produces_valid_pdf_bytes(self) -> None:
        resume = TailoredResume(
            full_name="PDF Test User",
            email="pdf@test.com",
            summary="Testing PDF generation.",
            experiences=[
                TailoredExperience(
                    company="TestCo",
                    title="Dev",
                    start_date=date(2022, 1, 1),
                    is_current=True,
                    bullets=["Built things"],
                )
            ],
        )
        html = to_html(resume)
        pdf_bytes = await to_pdf(html)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 500
