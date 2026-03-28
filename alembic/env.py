"""Alembic environment (async SQLAlchemy)."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.core.config import Settings, migration_database_url
from src.infrastructure.db.models.background_job import BackgroundJobModel  # noqa: F401
from src.infrastructure.db.models.base import Base
from src.infrastructure.db.models.quiz_attempt import QuizAttemptModel  # noqa: F401
from src.infrastructure.db.models.quiz_question import QuizQuestionModel  # noqa: F401
from src.infrastructure.db.models.submission import SubmissionModel  # noqa: F401
from src.infrastructure.db.models.task import TaskModel  # noqa: F401
from src.infrastructure.db.models.user import UserModel  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Alembic: прямой Postgres (DATABASE_URL_DIRECT) или тот же URL что и runtime."""
    return migration_database_url(Settings())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic context from a sync connection (run_sync callback)."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine."""
    settings = Settings()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = migration_database_url(settings)

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
