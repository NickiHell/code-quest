from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.entities.quiz import QuizQuestionData
from src.infrastructure.ai.routing_provider import RoutingAIProvider


def _settings(**kwargs: object) -> Settings:
    base = {
        "secret_key": "x" * 16,
        "database_url": "sqlite+aiosqlite:///:memory:",
        "redis_url": "redis://localhost:6379/0",
        "bot_token": "1234567890:ABCDEF-test",
        "webapp_url": "https://example.com/m/",
        "public_base_url": "https://example.com",
        "ai_backend": AiBackend.yandex_gpt,
    }
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def _stub_ai() -> AsyncMock:
    m = AsyncMock()
    m.evaluate_code = AsyncMock(return_value="ok")
    m.generate_quiz_question = AsyncMock(
        return_value=QuizQuestionData(
            question_text="q",
            options=tuple(f"o{i}" for i in range(5)),
            correct_index=0,
            grade="easy",
        ),
    )
    m.explain_quiz_choice = AsyncMock(return_value="because")
    return m


def test_init_requires_non_empty_providers() -> None:
    with pytest.raises(ValueError, match="Нет доступных"):
        RoutingAIProvider(_settings(), AsyncMock(), {})


@pytest.mark.asyncio
async def test_effective_backend_uses_redis_override_when_valid() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=AiBackend.yandex_gpt.value)
    inner = _stub_ai()
    router = RoutingAIProvider(
        _settings(ai_backend=AiBackend.yandex_gpt),
        redis,
        {AiBackend.yandex_gpt: inner},
    )
    await router.evaluate_code("c", "t")
    inner.evaluate_code.assert_awaited_once()
    redis.get.assert_awaited()


@pytest.mark.asyncio
async def test_effective_backend_falls_back_when_override_unknown() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="not_a_backend")
    inner = _stub_ai()
    router = RoutingAIProvider(
        _settings(ai_backend=AiBackend.yandex_gpt),
        redis,
        {AiBackend.yandex_gpt: inner},
    )
    await router.generate_quiz_question("easy", "t", None)
    inner.generate_quiz_question.assert_awaited_once()


@pytest.mark.asyncio
async def test_effective_backend_falls_back_when_override_not_configured() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=AiBackend.yandex_openai_responses.value)
    inner = _stub_ai()
    router = RoutingAIProvider(
        _settings(ai_backend=AiBackend.yandex_gpt),
        redis,
        {AiBackend.yandex_gpt: inner},
    )
    await router.explain_quiz_choice("q", tuple(f"x{i}" for i in range(5)), 0, 1)
    inner.explain_quiz_choice.assert_awaited_once()


@pytest.mark.asyncio
async def test_describe_runtime_ready_false_when_default_missing() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    inner = _stub_ai()
    router = RoutingAIProvider(
        _settings(ai_backend=AiBackend.yandex_openai_responses),
        redis,
        {AiBackend.yandex_gpt: inner},
    )
    data = await router.describe_runtime()
    assert data["ready"] is False
    assert data["effective"] == ""


@pytest.mark.asyncio
async def test_describe_runtime_override_invalid_string() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="???")
    inner = _stub_ai()
    router = RoutingAIProvider(
        _settings(ai_backend=AiBackend.yandex_gpt),
        redis,
        {AiBackend.yandex_gpt: inner},
    )
    data = await router.describe_runtime()
    assert data["override"] is None
