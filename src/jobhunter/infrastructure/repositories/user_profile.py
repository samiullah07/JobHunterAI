"""Async SQLAlchemy implementation of UserProfileRepository."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.infrastructure.db.models import (
    UserProfile,
)
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyUserProfileRepository(SQLAlchemyRepository[UserProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserProfile)

    async def get_with_children(self, id: uuid.UUID) -> UserProfile | None:
        stmt = (
            select(UserProfile)
            .where(UserProfile.id == id)
            .options(
                selectinload(UserProfile.work_experiences),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.projects),
                selectinload(UserProfile.certifications),
                selectinload(UserProfile.skills),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[UserProfile]:
        return await super().list(limit=limit, offset=offset)
