"""Pure domain DTOs for job matching and scoring."""

from __future__ import annotations

import uuid
from typing import Self

from pydantic import BaseModel, field_validator, model_validator


class ScoreComponents(BaseModel):
    """Individual scoring dimensions — each a float in [0, 1].

    Validation policy:
    - Numeric (int/float): accepted and clamped to [0, 1]. LLMs commonly overshoot.
    - Missing field: defaults to 0.0 — semantically "model did not score this dimension".
    - Non-numeric PRESENT value (None, str, list, dict): raises ValidationError.
      A present-but-malformed value indicates LLM output corruption, not a zero score.
    """

    skills: float = 0.0
    experience: float = 0.0
    location: float = 0.0
    salary: float = 0.0
    visa: float = 0.0
    remote: float = 0.0
    tech_stack: float = 0.0
    industry: float = 0.0
    culture: float = 0.0
    growth: float = 0.0

    @field_validator("*", mode="before")
    @classmethod
    def clamp_range(cls, v: object) -> float:
        if isinstance(v, bool):
            msg = "Score component must be a number, got bool"
            raise ValueError(msg)
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        msg = f"Score component must be a number, got {type(v).__name__}: {v!r}"
        raise ValueError(msg)


class WeightConfig(BaseModel):
    """Configurable weights per component — defaults sum to 1.0."""

    skills: float = 0.20
    experience: float = 0.15
    location: float = 0.05
    salary: float = 0.10
    visa: float = 0.05
    remote: float = 0.10
    tech_stack: float = 0.15
    industry: float = 0.05
    culture: float = 0.05
    growth: float = 0.10

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> Self:
        total = (
            self.skills
            + self.experience
            + self.location
            + self.salary
            + self.visa
            + self.remote
            + self.tech_stack
            + self.industry
            + self.culture
            + self.growth
        )
        if abs(total - 1.0) > 0.01:
            msg = f"Weights must sum to 1.0 (got {total:.4f})"
            raise ValueError(msg)
        return self

    def compute_overall(self, components: ScoreComponents) -> float:
        return (
            self.skills * components.skills
            + self.experience * components.experience
            + self.location * components.location
            + self.salary * components.salary
            + self.visa * components.visa
            + self.remote * components.remote
            + self.tech_stack * components.tech_stack
            + self.industry * components.industry
            + self.culture * components.culture
            + self.growth * components.growth
        )


class MatchResult(BaseModel):
    """Result of scoring a single job against a profile."""

    job_id: uuid.UUID
    profile_id: uuid.UUID
    overall: float
    components: ScoreComponents | None = None
    rationale: str | None = None
    passed_prefilter: bool = True
    prefilter_reasons: list[str] | None = None


class ScoringReport(BaseModel):
    """Summary of a scoring run."""

    scored: int = 0
    prefiltered_out: int = 0
    above_threshold: int = 0
    scoring_errors: int = 0
    top_results: list[MatchResult] = []
