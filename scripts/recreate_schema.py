"""Drop and recreate ALL tables directly from the ORM models."""
import asyncio

from jobhunter.infrastructure.db.base import Base
from jobhunter.infrastructure.db import models  # noqa: F401 — registers all tables
from jobhunter.infrastructure.db.session import _settings
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    engine = create_async_engine(_settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("SCHEMA RECREATED — all model tables now exist.")


if __name__ == "__main__":
    asyncio.run(main())