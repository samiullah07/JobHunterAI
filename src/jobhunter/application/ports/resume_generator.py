"""Resume generator port — interface for LLM-backed résumé tailoring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from jobhunter.domain.resume import TailoredResume
    from jobhunter.infrastructure.db.models import Job, UserProfile


class ResumeGenerator(Protocol):
    async def generate(self, profile: UserProfile, job: Job) -> TailoredResume: ...
