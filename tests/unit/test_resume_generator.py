"""Unit tests for the LLM résumé generator — fake LlmClient, no network."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from jobhunter.adapters.generation.llm_resume_generator import (
    LlmResumeGenerator,
    MalformedResumeError,
)


class FakeLlmClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.call_count = 0

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        self.call_count += 1
        return dict(self._response)


def _make_profile() -> MagicMock:
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
    profile.work_experiences = []
    profile.educations = []
    profile.projects = []
    profile.certifications = []
    return profile


def _make_job() -> MagicMock:
    job = MagicMock()
    job.title = "Backend Dev"
    job.company_name = "TechCo"
    job.location = "Remote"
    job.remote_policy = "remote"
    job.description_raw = "We need a Python backend developer."
    return job


_VALID_RESPONSE = {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "555-0100",
    "location": "NYC",
    "summary": "Python developer tailored for backend role.",
    "experiences": [],
    "education": [],
    "projects": [],
    "skills": [],
    "certifications": [],
    "keywords_used": ["python", "backend"],
}


class TestLlmResumeGenerator:
    async def test_parses_valid_response(self) -> None:
        llm = FakeLlmClient(_VALID_RESPONSE)
        gen = LlmResumeGenerator(llm_client=llm)
        result = await gen.generate(_make_profile(), _make_job())
        assert result.full_name == "Jane Doe"
        assert result.email == "jane@example.com"
        assert llm.call_count == 1

    async def test_malformed_response_raises(self) -> None:
        llm = FakeLlmClient({"invalid": "structure", "full_name": 123})
        gen = LlmResumeGenerator(llm_client=llm)
        with pytest.raises(MalformedResumeError, match="invalid"):
            await gen.generate(_make_profile(), _make_job())
