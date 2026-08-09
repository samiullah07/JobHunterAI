"""Async SQLAlchemy implementation of CoverLetterVersionRepository."""

from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.db.models import CoverLetterVersion
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyCoverLetterVersionRepository(SQLAlchemyRepository[CoverLetterVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CoverLetterVersion)
