"""CoverLetterVersion repository interface."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import CoverLetterVersion


class CoverLetterVersionRepository(Protocol):
    async def add(self, entity: CoverLetterVersion) -> CoverLetterVersion: ...
    async def get(self, id: uuid.UUID) -> CoverLetterVersion | None: ...
    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[CoverLetterVersion]: ...
    async def update(self, entity: CoverLetterVersion) -> CoverLetterVersion: ...
    async def delete(self, id: uuid.UUID) -> None: ...
