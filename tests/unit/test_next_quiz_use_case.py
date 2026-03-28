from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.entities.quiz import QuizQuestionData, QuizQuestionPublic
from src.use_cases.next_quiz import NextQuizUseCase


def _q(text: str = "Вопрос?") -> QuizQuestionData:
    opts = tuple(f"v{i}" for i in range(5))
    return QuizQuestionData(
        question_text=text,
        options=opts,
        correct_index=0,
        grade="easy",
    )


@pytest.mark.asyncio
async def test_execute_saves_after_fingerprint_accepted() -> None:
    users = AsyncMock()
    users.get_or_create_by_telegram_id = AsyncMock()
    questions = AsyncMock()
    questions.create = AsyncMock(return_value=77)
    ai = AsyncMock()
    ai.generate_quiz_question = AsyncMock(return_value=_q())
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.sismember = AsyncMock(return_value=False)
    pipe = MagicMock()
    pipe.incr = MagicMock()
    pipe.sadd = MagicMock()
    pipe.expire = MagicMock()
    pipe.lpush = MagicMock()
    pipe.ltrim = MagicMock()
    pipe.execute = AsyncMock(return_value=[3, True, True, 1, True, True])
    redis.pipeline = MagicMock(return_value=pipe)

    uc = NextQuizUseCase(users=users, questions=questions, ai=ai, redis=redis)
    out = await uc.execute(telegram_id=1, username="u", grade="easy", topic="python")
    assert isinstance(out, QuizQuestionPublic)
    assert out.id == 77
    assert out.question_number == 3
    users.get_or_create_by_telegram_id.assert_awaited_once()
    questions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_retries_on_duplicate_fingerprint() -> None:
    users = AsyncMock()
    users.get_or_create_by_telegram_id = AsyncMock()
    questions = AsyncMock()
    questions.create = AsyncMock(return_value=1)
    ai = AsyncMock()
    ai.generate_quiz_question = AsyncMock(return_value=_q("same"))
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"legacy"])
    redis.sismember = AsyncMock(side_effect=[True, False])
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, True, True, 1, True, True])
    redis.pipeline = MagicMock(return_value=pipe)

    uc = NextQuizUseCase(users=users, questions=questions, ai=ai, redis=redis)
    await uc.execute(telegram_id=2, username=None, grade="easy", topic=None)
    assert ai.generate_quiz_question.await_count == 2


@pytest.mark.asyncio
async def test_execute_raises_when_always_duplicate() -> None:
    users = AsyncMock()
    users.get_or_create_by_telegram_id = AsyncMock()
    questions = AsyncMock()
    ai = AsyncMock()
    ai.generate_quiz_question = AsyncMock(return_value=_q())
    redis = AsyncMock()
    redis.lrange = AsyncMock(return_value=[])
    redis.sismember = AsyncMock(return_value=True)
    pipe = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)

    uc = NextQuizUseCase(users=users, questions=questions, ai=ai, redis=redis)
    with pytest.raises(ValueError, match="уникальный"):
        await uc.execute(telegram_id=3, username=None, grade="easy", topic="algorithms")
    questions.create.assert_not_called()
