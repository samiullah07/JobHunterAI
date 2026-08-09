"""Unit tests for the LLM cover letter generator — fake LlmClient, no network."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from jobhunter.adapters.generation.llm_cover_letter_generator import (
    LlmCoverLetterGenerator,
    MalformedCoverLetterError,
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


_VALID_RESPONSE: dict[str, Any] = {
    "salutation": "Dear Hiring Manager,",
    "opening": "I am writing about the Backend Dev role at TechCo.",
    "body_paragraphs": [
        "My background in Python makes me a strong candidate.",
        "I am eager to contribute to TechCo's engineering team.",
    ],
    "closing": "Thank you for considering my application.",
    "signature": "Sincerely, Jane Doe",
    "company_name": "TechCo",
    "role": "Backend Dev",
}


class TestLlmCoverLetterGenerator:
    async def test_parses_valid_response(self) -> None:
        llm = FakeLlmClient(_VALID_RESPONSE)
        gen = LlmCoverLetterGenerator(llm_client=llm)
        result = await gen.generate(_make_profile(), _make_job())
        assert result.salutation == "Dear Hiring Manager,"
        assert result.company_name == "TechCo"
        assert result.role == "Backend Dev"
        assert len(result.body_paragraphs) == 2
        assert llm.call_count == 1

    async def test_malformed_response_raises(self) -> None:
        llm = FakeLlmClient({"invalid": "structure"})
        gen = LlmCoverLetterGenerator(llm_client=llm)
        with pytest.raises(MalformedCoverLetterError):
            await gen.generate(_make_profile(), _make_job())
