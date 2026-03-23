"""Тесты начисления очков за квиз (одна зачётная попытка на вопрос)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.quiz_repositories import (
    AbstractQuizAttemptRepository,
    AbstractQuizQuestionRepository,
)
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.quiz import QuizQuestionData
from src.entities.user import User
from src.use_cases.submit_quiz import SubmitQuizUseCase


def _user() -> User:
    return User(
        id=1,
        telegram_id=100,
        username="t",
        created_at=datetime.now(tz=UTC),
        score=0,
    )


def _question() -> QuizQuestionData:
    return QuizQuestionData(
        question_text="Q?",
        options=("a", "b", "c", "d", "e"),
        correct_index=2,
        grade="junior",
    )


@pytest.mark.asyncio
async def test_first_answer_correct_gets_points() -> None:
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_telegram_id = AsyncMock(return_value=_user())
    users.update = AsyncMock(side_effect=lambda u: u)

    questions = AsyncMock(spec=AbstractQuizQuestionRepository)
    questions.get_by_id = AsyncMock(return_value=_question())

    attempts = AsyncMock(spec=AbstractQuizAttemptRepository)
    attempts.count_attempts = AsyncMock(return_value=0)
    attempts.create = AsyncMock(return_value=99)

    ai = AsyncMock(spec=AbstractAIProvider)
    ai.explain_quiz_choice = AsyncMock(return_value="Ок.")

    leaderboard = AsyncMock(spec=AbstractLeaderboard)

    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=ai,
        leaderboard=leaderboard,
    )
    result = await uc.execute(telegram_id=100, question_id=5, chosen_index=2)

    assert result.is_correct is True
    assert result.score == 5
    assert "Повторный ответ" not in result.feedback
    leaderboard.add_score.assert_awaited_once_with(user_id=1, points=5)


@pytest.mark.asyncio
async def test_second_answer_no_points_even_if_correct() -> None:
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_telegram_id = AsyncMock(return_value=_user())
    users.update = AsyncMock(side_effect=lambda u: u)

    questions = AsyncMock(spec=AbstractQuizQuestionRepository)
    questions.get_by_id = AsyncMock(return_value=_question())

    attempts = AsyncMock(spec=AbstractQuizAttemptRepository)
    attempts.count_attempts = AsyncMock(return_value=1)
    attempts.create = AsyncMock(return_value=100)

    ai = AsyncMock(spec=AbstractAIProvider)
    ai.explain_quiz_choice = AsyncMock(return_value="Ок.")

    leaderboard = AsyncMock(spec=AbstractLeaderboard)

    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=ai,
        leaderboard=leaderboard,
    )
    result = await uc.execute(telegram_id=100, question_id=5, chosen_index=2)

    assert result.is_correct is True
    assert result.score == 0
    assert "Повторный ответ" in result.feedback
    leaderboard.add_score.assert_awaited_once_with(user_id=1, points=0)
