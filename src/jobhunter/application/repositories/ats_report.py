"""AtsReport repository interface."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import AtsReport


class AtsReportRepository(Protocol):
    async def add(self, entity: AtsReport) -> AtsReport: ...
    async def get(self, id: uuid.UUID) -> AtsReport | None: ...
    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[AtsReport]: ...
    async def update(self, entity: AtsReport) -> AtsReport: ...
    async def delete(self, id: uuid.UUID) -> None: ...
