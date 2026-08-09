"""LLM-backed job scorer — implements the JobScorer port."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from pydantic import ValidationError

from jobhunter.domain.scoring import ScoreComponents

if TYPE_CHECKING:
    from jobhunter.application.ports.llm import LlmClient
    from jobhunter.infrastructure.db.models import Job, UserProfile

logger = structlog.get_logger()


class MalformedScoreError(Exception):
    """Raised when LLM returns component data that fails ScoreComponents validation."""


_SYSTEM_PROMPT = """\
You are a job-match scoring engine. Given a candidate profile and a job description,
score the match on each dimension from 0.0 to 1.0.

RULES:
- Score ONLY against the provided profile facts. Do NOT invent or assume skills,
  experience, or qualifications not explicitly present in the profile.
- If the job requires something not in the profile, score that dimension lower.
- Provide a brief rationale explaining your scores.

Return ONLY a JSON object with this structure:
{
  "skills": 0.0-1.0,
  "experience": 0.0-1.0,
  "location": 0.0-1.0,
  "salary": 0.0-1.0,
  "visa": 0.0-1.0,
  "remote": 0.0-1.0,
  "tech_stack": 0.0-1.0,
  "industry": 0.0-1.0,
  "culture": 0.0-1.0,
  "growth": 0.0-1.0,
  "rationale": "brief explanation"
}
"""


def _render_profile(profile: UserProfile) -> str:
    """Render verified profile data as text for the scoring prompt."""
    parts = [f"Name: {profile.full_name}", f"Headline: {profile.headline or 'N/A'}"]

    if profile.summary:
        parts.append(f"Summary: {profile.summary}")
    if profile.location:
        parts.append(f"Location: {profile.location}")
    if profile.remote_preference:
        parts.append(f"Remote preference: {profile.remote_preference}")
    if profile.salary_min or profile.salary_max:
        parts.append(
            f"Salary range: {profile.salary_min or '?'} - {profile.salary_max or '?'} "
            f"{profile.salary_currency or 'USD'}"
        )
    if profile.visa_status:
        parts.append(f"Visa status: {profile.visa_status}")

    if profile.skills:
        skills_text = ", ".join(f"{s.name} ({s.proficiency or 'unknown'})" for s in profile.skills)
        parts.append(f"Skills: {skills_text}")

    if profile.work_experiences:
        parts.append("Work Experience:")
        for exp in profile.work_experiences:
            end = "present" if exp.is_current else str(exp.end_date or "?")
            parts.append(f"  - {exp.title} at {exp.company_name} ({exp.start_date} to {end})")
            if exp.technologies:
                parts.append(f"    Tech: {', '.join(exp.technologies)}")

    if profile.preferred_industries:
        parts.append(f"Preferred industries: {', '.join(profile.preferred_industries)}")
    if profile.keywords:
        parts.append(f"Keywords: {', '.join(profile.keywords)}")

    return "\n".join(parts)


def _render_job(job: Job) -> str:
    """Render job posting data for the scoring prompt."""
    parts = [
        f"Title: {job.title}",
        f"Company: {job.company_name}",
    ]
    if job.location:
        parts.append(f"Location: {job.location}")
    if job.remote_policy:
        parts.append(f"Remote policy: {job.remote_policy}")
    if job.salary_min or job.salary_max:
        parts.append(
            f"Salary: {job.salary_min or '?'} - {job.salary_max or '?'} "
            f"{job.salary_currency or 'USD'}"
        )
    if job.employment_type:
        parts.append(f"Type: {job.employment_type}")
    if job.description_raw:
        desc = job.description_raw[:3000]
        parts.append(f"Description:\n{desc}")
    return "\n".join(parts)


class LlmJobScorer:
    """Scores jobs against profiles using LLM-generated qualitative components."""

    def __init__(self, llm_client: LlmClient) -> None:
        self._llm = llm_client

    async def score(self, job: Job, profile: UserProfile) -> tuple[ScoreComponents, str]:
        user_prompt = (
            f"## Candidate Profile\n{_render_profile(profile)}\n\n"
            f"## Job Posting\n{_render_job(job)}"
        )

        raw: dict[str, Any] = await self._llm.complete_json(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            schema_hint="ScoreComponents + rationale",
        )

        rationale = str(raw.pop("rationale", ""))

        try:
            components = ScoreComponents(
                skills=raw.get("skills", 0.0),
                experience=raw.get("experience", 0.0),
                location=raw.get("location", 0.0),
                salary=raw.get("salary", 0.0),
                visa=raw.get("visa", 0.0),
                remote=raw.get("remote", 0.0),
                tech_stack=raw.get("tech_stack", 0.0),
                industry=raw.get("industry", 0.0),
                culture=raw.get("culture", 0.0),
                growth=raw.get("growth", 0.0),
            )
        except ValidationError as exc:
            logger.warning(
                "malformed_llm_score",
                job_id=str(getattr(job, "id", "?")),
                error=str(exc),
            )
            raise MalformedScoreError(f"LLM returned non-numeric score components: {exc}") from exc

        return components, rationale
