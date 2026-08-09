"""Async unit-of-work: yields session, commits on success, rolls back on exception."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from jobhunter.config import get_settings

_settings = get_settings()


@asynccontextmanager
async def unit_of_work() -> AsyncGenerator[AsyncSession]:
    """Create a fresh engine+session, commit on success, roll back on error."""
    engine = create_async_engine(
        _settings.database_url,
        echo=(_settings.app_env == "dev"),
    )
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
    finally:
        await engine.dispose()