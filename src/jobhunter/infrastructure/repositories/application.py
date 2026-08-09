"""Async SQLAlchemy implementation of ApplicationRepository."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.infrastructure.db.models import Application
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyApplicationRepository(SQLAlchemyRepository[Application]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Application)

    async def get_by_job_profile(
        self, job_id: uuid.UUID, profile_id: uuid.UUID
    ) -> Application | None:
        stmt = select(Application).where(
            Application.job_id == job_id, Application.profile_id == profile_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(self, status: str, *, limit: int = 100) -> Sequence[Application]:
        stmt = select(Application).where(Application.status == status).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_review_packet(self, application_id: uuid.UUID) -> Application | None:
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.job),
                selectinload(Application.answers),
                selectinload(Application.screenshots),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Application]:
        return await super().list(limit=limit, offset=offset)
