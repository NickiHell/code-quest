"""Pytest fixtures."""

from __future__ import annotations

import os
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
from src.infrastructure.db.models import quiz_attempt as quiz_attempt_model  # noqa: F401
from src.infrastructure.db.models import quiz_question as quiz_question_model  # noqa: F401
from src.infrastructure.db.models import submission as submission_model  # noqa: F401
from src.infrastructure.db.models import task as task_model  # noqa: F401
from src.infrastructure.db.models import user as user_model  # noqa: F401
from src.infrastructure.db.models.base import Base

os.environ.setdefault("SECRET_KEY", "test-secret-key-please-change")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("BOT_TOKEN", "1234567890:ABCDEF-test-token")
os.environ.setdefault("WEBAPP_URL", "https://example.com/miniapp/")
os.environ.setdefault("PUBLIC_BASE_URL", "https://example.com")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-for-ci-16")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("LOG_DIR", "")


@pytest.fixture
async def async_db_session() -> AsyncIterator[AsyncSession]:
    """In-memory SQLite session with automatic rollback after each test."""
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
    """Stub AI provider returning deterministic feedback."""
    mock = AsyncMock(spec=AbstractAIProvider)
    mock.evaluate_code = AsyncMock(return_value="Excellent solution.")
    mock.generate_quiz_question = AsyncMock(
        return_value=QuizQuestionData(
            question_text="Тестовый вопрос?",
            options=tuple(f"Вариант {i}" for i in range(5)),
            correct_index=0,
            grade="junior",
        ),
    )
    mock.explain_quiz_choice = AsyncMock(return_value="Краткий фидбек.")
    return mock


@pytest.fixture
async def redis_client() -> AsyncIterator[redis_async.Redis]:
    """Best-effort async Redis client for integration tests (skipped if unavailable)."""
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
