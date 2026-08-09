"""Async engine and session factory (lazy-creation version)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from jobhunter.config import get_settings

_settings = get_settings()


async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    Create a fresh async engine and session within the currently running
    event loop. This ensures the engine's connections are bound to a live
    loop and avoids the `'NoneType' object has no attribute 'send'` error
    that occurs when an engine is created with a dead loop.

    The engine is explicitly disposed after use to prevent connection
    leaks and "another operation is in progress" errors when the function
    is called multiple times (e.g., on Streamlit reruns).
    """
    engine = create_async_engine(
        _settings.database_url,
        echo=(_settings.app_env == "dev"),
        poolclass=None,  # Use NullPool to prevent connection reuse across loops
    )
    async_session_factory = async_sessionmaker(
        engine, expire_on_commit=False
    )

    try:
        async with async_session_factory() as session:
            yield session
    finally:
        # Dispose the engine to close all connections before the loop exits
        await engine.dispose()


async def get_session_with_engine() -> AsyncGenerator[AsyncSession]:
    """
    Alternative: Create a session with an engine that persists for the lifetime
    of the async generator context. Use when multiple queries need the same engine.
    """
    engine = create_async_engine(
        _settings.database_url,
        echo=(_settings.app_env == "dev"),
    )
    async_session_factory = async_sessionmaker(
        engine, expire_on_commit=False
    )

    try:
        async with async_session_factory() as session:
            yield session
    finally:
        await engine.dispose()