"""Тесты NextQuizUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.quiz_repositories import AbstractQuizQuestionRepository
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.quiz import QuizQuestionData
from src.entities.user import User
from src.use_cases.next_quiz import NextQuizUseCase


@pytest.mark.asyncio
async def test_next_quiz_returns_personal_question_number() -> None:
    qdata = QuizQuestionData(
        question_text="2+2=?",
        options=("1", "2", "3", "4", "5"),
        correct_index=3,
        grade="medium",
    )

    users = AsyncMock(spec=AbstractUserRepository)
    users.get_or_create_by_telegram_id = AsyncMock(
        return_value=User(
            id=1,
            telegram_id=99,
            username="t",
            created_at=datetime.now(tz=UTC),
            score=0,
        ),
    )

    questions = AsyncMock(spec=AbstractQuizQuestionRepository)
    questions.create = AsyncMock(return_value=42)

    ai = AsyncMock(spec=AbstractAIProvider)
    ai.generate_quiz_question = AsyncMock(return_value=qdata)

    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.sismember = AsyncMock(return_value=False)

    pipe = MagicMock()
    pipe.incr = MagicMock(return_value=pipe)
    pipe.sadd = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.lpush = MagicMock(return_value=pipe)
    pipe.ltrim = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[7, 1, True, 1, True, True])
    redis.pipeline = MagicMock(return_value=pipe)

    uc = NextQuizUseCase(users=users, questions=questions, ai=ai, redis=redis)
    out = await uc.execute(telegram_id=99, username="t", grade="medium", topic="python")

    assert out.id == 42
    assert out.question_number == 7
    assert out.question_text == qdata.question_text
