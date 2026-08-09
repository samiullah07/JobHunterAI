"""Fake job scorer for deterministic offline testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobhunter.domain.scoring import ScoreComponents

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import Job, UserProfile


class FakeJobScorer:
    """Returns fixed scores; tracks call count to verify prefilter skips LLM."""

    def __init__(
        self,
        components: ScoreComponents | None = None,
        rationale: str = "Fake scorer rationale",
    ) -> None:
        self._components = components or ScoreComponents(
            skills=0.8,
            experience=0.7,
            location=0.6,
            salary=0.9,
            visa=1.0,
            remote=0.8,
            tech_stack=0.75,
            industry=0.5,
            culture=0.6,
            growth=0.7,
        )
        self._rationale = rationale
        self.call_count = 0

    async def score(self, job: Job, profile: UserProfile) -> tuple[ScoreComponents, str]:
        self.call_count += 1
        return self._components, self._rationale
