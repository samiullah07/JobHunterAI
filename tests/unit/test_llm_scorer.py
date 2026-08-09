"""Unit tests for the LLM job scorer — uses FakeLlmClient, no network."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from jobhunter.adapters.scoring.llm_job_scorer import (
    LlmJobScorer,
    MalformedScoreError,
    _render_profile,
)


class FakeLlmClient:
    """Records calls and returns canned JSON."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[tuple[str, str, str]] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        self.calls.append((system, user, schema_hint))
        return dict(self._response)


def _make_profile() -> MagicMock:
    profile = MagicMock()
    profile.full_name = "Jane Doe"
    profile.headline = "Senior Engineer"
    profile.summary = "10 years Python."
    profile.location = "NYC"
    profile.remote_preference = "remote"
    profile.salary_min = 120000.0
    profile.salary_max = 180000.0
    profile.salary_currency = "USD"
    profile.visa_status = None
    profile.preferred_industries = ["fintech", "saas"]
    profile.keywords = ["python", "distributed systems"]

    skill1 = MagicMock()
    skill1.name = "Python"
    skill1.proficiency = "Expert"
    skill2 = MagicMock()
    skill2.name = "PostgreSQL"
    skill2.proficiency = "Advanced"
    profile.skills = [skill1, skill2]

    exp = MagicMock()
    exp.title = "Staff Engineer"
    exp.company_name = "BigCo"
    exp.start_date = "2020-01-01"
    exp.end_date = None
    exp.is_current = True
    exp.technologies = ["Python", "Kafka"]
    profile.work_experiences = [exp]

    return profile


def _make_job() -> MagicMock:
    job = MagicMock()
    job.title = "Backend Engineer"
    job.company_name = "StartupX"
    job.location = "Remote"
    job.remote_policy = "remote"
    job.salary_min = 130000.0
    job.salary_max = 160000.0
    job.salary_currency = "USD"
    job.employment_type = "full_time"
    job.description_raw = "We need a Python backend engineer with Kafka experience."
    return job


class TestLlmJobScorer:
    async def test_returns_components_and_rationale(self) -> None:
        llm = FakeLlmClient(
            {
                "skills": 0.9,
                "experience": 0.8,
                "location": 0.7,
                "salary": 0.85,
                "visa": 1.0,
                "remote": 0.95,
                "tech_stack": 0.9,
                "industry": 0.6,
                "culture": 0.5,
                "growth": 0.7,
                "rationale": "Strong Python match with Kafka experience.",
            }
        )
        scorer = LlmJobScorer(llm_client=llm)
        components, rationale = await scorer.score(_make_job(), _make_profile())

        assert components.skills == 0.9
        assert components.tech_stack == 0.9
        assert rationale == "Strong Python match with Kafka experience."
        assert llm.call_count == 1

    async def test_prompt_contains_profile_facts(self) -> None:
        llm = FakeLlmClient(
            {
                "skills": 0.5,
                "experience": 0.5,
                "location": 0.5,
                "salary": 0.5,
                "visa": 0.5,
                "remote": 0.5,
                "tech_stack": 0.5,
                "industry": 0.5,
                "culture": 0.5,
                "growth": 0.5,
                "rationale": "ok",
            }
        )
        scorer = LlmJobScorer(llm_client=llm)
        await scorer.score(_make_job(), _make_profile())

        _, user_prompt, _ = llm.calls[0]
        assert "Jane Doe" in user_prompt
        assert "Python" in user_prompt
        assert "Staff Engineer" in user_prompt
        assert "BigCo" in user_prompt

    async def test_clamps_out_of_range_values(self) -> None:
        llm = FakeLlmClient(
            {
                "skills": 1.5,
                "experience": -0.3,
                "location": 0.5,
                "salary": 0.5,
                "visa": 0.5,
                "remote": 0.5,
                "tech_stack": 0.5,
                "industry": 0.5,
                "culture": 0.5,
                "growth": 0.5,
                "rationale": "clamped",
            }
        )
        scorer = LlmJobScorer(llm_client=llm)
        components, _ = await scorer.score(_make_job(), _make_profile())

        assert components.skills == 1.0
        assert components.experience == 0.0

    async def test_malformed_non_numeric_raises(self) -> None:
        llm = FakeLlmClient(
            {
                "skills": "high",
                "experience": 0.8,
                "location": 0.5,
                "salary": 0.5,
                "visa": 0.5,
                "remote": 0.5,
                "tech_stack": 0.5,
                "industry": 0.5,
                "culture": 0.5,
                "growth": 0.5,
                "rationale": "malformed",
            }
        )
        scorer = LlmJobScorer(llm_client=llm)
        with pytest.raises(MalformedScoreError, match="non-numeric"):
            await scorer.score(_make_job(), _make_profile())

    async def test_malformed_none_value_raises(self) -> None:
        llm = FakeLlmClient(
            {
                "skills": 0.8,
                "experience": None,
                "location": 0.5,
                "salary": 0.5,
                "visa": 0.5,
                "remote": 0.5,
                "tech_stack": 0.5,
                "industry": 0.5,
                "culture": 0.5,
                "growth": 0.5,
                "rationale": "has None",
            }
        )
        scorer = LlmJobScorer(llm_client=llm)
        with pytest.raises(MalformedScoreError):
            await scorer.score(_make_job(), _make_profile())


class TestRenderProfile:
    def test_renders_verified_facts_only(self) -> None:
        profile = _make_profile()
        text = _render_profile(profile)
        assert "Jane Doe" in text
        assert "Python" in text
        assert "120000" in text
