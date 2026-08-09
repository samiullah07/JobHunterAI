"""Job scorer port — interface for LLM-backed qualitative scoring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from jobhunter.domain.scoring import ScoreComponents
    from jobhunter.infrastructure.db.models import Job, UserProfile


class JobScorer(Protocol):
    async def score(self, job: Job, profile: UserProfile) -> tuple[ScoreComponents, str]: ...
