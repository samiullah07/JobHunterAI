"""ResumeVersion repository interface."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import ResumeVersion


class ResumeVersionRepository(Protocol):
    async def add(self, entity: ResumeVersion) -> ResumeVersion: ...
    async def get(self, id: uuid.UUID) -> ResumeVersion | None: ...
    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ResumeVersion]: ...
    async def update(self, entity: ResumeVersion) -> ResumeVersion: ...
    async def delete(self, id: uuid.UUID) -> None: ...
