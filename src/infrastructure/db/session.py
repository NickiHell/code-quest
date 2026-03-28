from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Build an async engine for PostgreSQL (asyncpg) or SQLite."""
    url = str(settings.database_url)
    if url.startswith("sqlite+"):
        return create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
        )
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"statement_cache_size": 0},
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory with sane defaults for API handlers."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
