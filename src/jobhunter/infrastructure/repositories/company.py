"""Async SQLAlchemy implementation of CompanyRepository."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.db.models import Company
from jobhunter.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyCompanyRepository(SQLAlchemyRepository[Company]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Company)

    async def get_by_name(self, name: str) -> Company | None:
        stmt = select(Company).where(Company.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_by_name(self, name: str, **fields: Any) -> Company:
        existing = await self.get_by_name(name)
        if existing is not None:
            for key, value in fields.items():
                setattr(existing, key, value)
            await self._session.flush()
            return existing
        company = Company(id=uuid.uuid4(), name=name, **fields)
        self._session.add(company)
        await self._session.flush()
        return company

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[Company]:
        return await super().list(limit=limit, offset=offset)
