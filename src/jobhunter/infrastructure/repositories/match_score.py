"""Async SQLAlchemy implementation of MatchScoreRepository."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.db.models import MatchScore
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyMatchScoreRepository(SQLAlchemyRepository[MatchScore]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MatchScore)

    async def get_for_job_profile(
        self, job_id: uuid.UUID, profile_id: uuid.UUID
    ) -> MatchScore | None:
        stmt = select(MatchScore).where(
            MatchScore.job_id == job_id, MatchScore.profile_id == profile_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_above_threshold(
        self, profile_id: uuid.UUID, threshold: float, *, limit: int = 100
    ) -> Sequence[MatchScore]:
        stmt = (
            select(MatchScore)
            .where(MatchScore.profile_id == profile_id, MatchScore.overall >= threshold)
            .order_by(MatchScore.overall.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[MatchScore]:
        return await super().list(limit=limit, offset=offset)
