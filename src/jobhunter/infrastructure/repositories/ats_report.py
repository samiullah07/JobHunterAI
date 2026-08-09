"""Async SQLAlchemy implementation of AtsReportRepository."""

from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.db.models import AtsReport
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyAtsReportRepository(SQLAlchemyRepository[AtsReport]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AtsReport)
