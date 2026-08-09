"""Shared test fixtures."""

import shutil
import subprocess
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from jobhunter.infrastructure.db import models  # noqa: F401
from jobhunter.infrastructure.db.base import Base


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=False)
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_url() -> str:
    if not _docker_available():
        pytest.skip("Docker not available")
    return "postgresql+asyncpg://jobhunter:jobhunter@localhost:5433/jobhunter"


@pytest_asyncio.fixture(scope="session")
async def _setup_schema(db_url: str) -> AsyncGenerator[str]:
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield db_url
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(_setup_schema: str) -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(_setup_schema, echo=False)
    async with engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        yield session
        await session.close()
        await txn.rollback()
    await engine.dispose()
