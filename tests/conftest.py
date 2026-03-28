from __future__ import annotations

import asyncio
import atexit
import contextlib
import os
import tempfile
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as redis_async
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.entities.quiz import QuizQuestionData
from src.infrastructure.db.models import background_job as background_job_model  # noqa: F401
from src.infrastructure.db.models import quiz_attempt as quiz_attempt_model  # noqa: F401
from src.infrastructure.db.models import quiz_question as quiz_question_model  # noqa: F401
from src.infrastructure.db.models import submission as submission_model  # noqa: F401
from src.infrastructure.db.models import task as task_model  # noqa: F401
from src.infrastructure.db.models import user as user_model  # noqa: F401
from src.infrastructure.db.models.base import Base

os.environ.setdefault("SECRET_KEY", "test-secret-key-please-change")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("BOT_TOKEN", "1234567890:ABCDEF-test-token")
os.environ.setdefault("WEBAPP_URL", "https://example.com/miniapp/")
os.environ.setdefault("PUBLIC_BASE_URL", "https://example.com")
os.environ.setdefault("LOG_DIR", "")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "0123456789abcdef")
os.environ.setdefault("TELEGRAM_SET_WEBHOOK_ON_STARTUP", "false")

_fd, _TEST_DB_PATH = tempfile.mkstemp(suffix=".codequest-test.sqlite")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"


def _cleanup_test_db() -> None:
    with contextlib.suppress(OSError):
        os.unlink(_TEST_DB_PATH)


atexit.register(_cleanup_test_db)


def _init_shared_db_schema() -> None:
    """Один файл SQLite для интеграции API + фоновых задач (Celery в тестах мокается)."""

    async def go() -> None:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(go())


_init_shared_db_schema()


@pytest.fixture
async def async_db_session() -> AsyncIterator[AsyncSession]:
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()

    await engine.dispose()


@pytest.fixture
def mock_ai_service() -> AbstractAIProvider:
    mock = AsyncMock(spec=AbstractAIProvider)
    mock.evaluate_code = AsyncMock(return_value="Excellent solution.")
    mock.generate_quiz_question = AsyncMock(
        return_value=QuizQuestionData(
            question_text="Тестовый вопрос?",
            options=tuple(f"Вариант {i}" for i in range(5)),
            correct_index=0,
            grade="easy",
        ),
    )
    mock.explain_quiz_choice = AsyncMock(return_value="Краткий фидбек.")
    return mock


@pytest.fixture
async def redis_client() -> AsyncIterator[redis_async.Redis]:
    url = os.environ["REDIS_URL"]
    client = redis_async.from_url(url, decode_responses=True)
    try:
        await client.ping()
    except Exception:  # noqa: BLE001
        await client.aclose()
        pytest.skip("Redis is not available")
    try:
        yield client
    finally:
        await client.aclose()
