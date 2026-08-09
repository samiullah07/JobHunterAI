"""Cover letter generator port — provider-agnostic interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from jobhunter.domain.cover_letter import CoverLetter

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import Job, UserProfile


class CoverLetterGenerator(Protocol):
    async def generate(self, profile: UserProfile, job: Job) -> CoverLetter: ...
