"""Async SQLAlchemy implementation of JobRepository."""

import uuid
from collections.abc import Sequence

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.infrastructure.db.models import Job, MatchScore
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyJobRepository(SQLAlchemyRepository[Job]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Job)

    async def get_by_source_external(self, source: str, external_id: str) -> Job | None:
        stmt = select(Job).where(Job.source == source, Job.external_id == external_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_source_external(self, source: str, external_id: str) -> bool:
        stmt = select(exists().where(Job.source == source, Job.external_id == external_id))
        result = await self._session.execute(stmt)
        return bool(result.scalar())

    async def list_unscored(self, profile_id: uuid.UUID, *, limit: int = 100) -> Sequence[Job]:
        scored_job_ids = select(MatchScore.job_id).where(MatchScore.profile_id == profile_id)
        stmt = (
            select(Job)
            .where(Job.id.notin_(scored_job_ids))
            .options(selectinload(Job.company))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Job]:
        return await super().list(limit=limit, offset=offset)
