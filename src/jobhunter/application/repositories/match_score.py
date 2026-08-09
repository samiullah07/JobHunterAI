"""MatchScore repository interface."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import MatchScore


class MatchScoreRepository(Protocol):
    async def add(self, entity: MatchScore) -> MatchScore: ...
    async def get(self, id: uuid.UUID) -> MatchScore | None: ...
    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[MatchScore]: ...
    async def update(self, entity: MatchScore) -> MatchScore: ...
    async def delete(self, id: uuid.UUID) -> None: ...
    async def get_for_job_profile(
        self, job_id: uuid.UUID, profile_id: uuid.UUID
    ) -> MatchScore | None: ...
    async def list_above_threshold(
        self, profile_id: uuid.UUID, threshold: float, *, limit: int = 100
    ) -> Sequence[MatchScore]: ...
