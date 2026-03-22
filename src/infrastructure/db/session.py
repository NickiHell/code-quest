"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Build an async engine for PostgreSQL (asyncpg)."""
    return create_async_engine(
        str(settings.database_url),
        echo=settings.app_env == "development",
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory with sane defaults for API handlers."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
