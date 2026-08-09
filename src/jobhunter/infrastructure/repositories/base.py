"""Generic async SQLAlchemy repository base implementation."""

import uuid
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class SQLAlchemyRepository(Generic[ModelT]):  # noqa: UP046
    def __init__(self, session: AsyncSession, model_class: type[ModelT]) -> None:
        self._session = session
        self._model_class = model_class

    async def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get(self, id: uuid.UUID) -> ModelT | None:
        return await self._session.get(self._model_class, id)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self._model_class).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update(self, entity: ModelT) -> ModelT:
        merged = await self._session.merge(entity)
        await self._session.flush()
        return merged

    async def delete(self, id: uuid.UUID) -> None:
        entity = await self.get(id)
        if entity is not None:
            await self._session.delete(entity)
            await self._session.flush()
