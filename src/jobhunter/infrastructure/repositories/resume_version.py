"""Async SQLAlchemy implementation of ResumeVersionRepository."""

from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.db.models import ResumeVersion
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyResumeVersionRepository(SQLAlchemyRepository[ResumeVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ResumeVersion)
