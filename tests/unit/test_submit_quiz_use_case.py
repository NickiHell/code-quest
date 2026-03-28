from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import NotFoundError
from src.entities.quiz import QuizQuestionData
from src.use_cases.submit_quiz import SubmitQuizUseCase


def _opts() -> tuple[str, str, str, str, str]:
    return tuple(f"o{i}" for i in range(5))


@pytest.mark.asyncio
async def test_submit_negative_index_raises(async_db_session) -> None:
    from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
    from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    users = SQLAlchemyUserRepository(async_db_session)
    questions = SQLAlchemyQuizQuestionRepository(async_db_session)
    attempts = SQLAlchemyQuizAttemptRepository(async_db_session)
    ai = AsyncMock()
    lb = AsyncMock()
    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=ai,
        leaderboard=lb,
    )
    with pytest.raises(ValueError, match="non-negative"):
        await uc.execute(telegram_id=1, question_id=1, chosen_index=-1)


@pytest.mark.asyncio
async def test_submit_user_not_found(async_db_session) -> None:
    from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
    from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    users = SQLAlchemyUserRepository(async_db_session)
    questions = SQLAlchemyQuizQuestionRepository(async_db_session)
    attempts = SQLAlchemyQuizAttemptRepository(async_db_session)
    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=AsyncMock(),
        leaderboard=AsyncMock(),
    )
    with pytest.raises(NotFoundError, match="User"):
        await uc.execute(telegram_id=999, question_id=1, chosen_index=0)


@pytest.mark.asyncio
async def test_submit_question_not_found(async_db_session) -> None:
    from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
    from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    users = SQLAlchemyUserRepository(async_db_session)
    await users.create(1, None)
    questions = SQLAlchemyQuizQuestionRepository(async_db_session)
    attempts = SQLAlchemyQuizAttemptRepository(async_db_session)
    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=AsyncMock(),
        leaderboard=AsyncMock(),
    )
    with pytest.raises(NotFoundError, match="Question"):
        await uc.execute(telegram_id=1, question_id=404, chosen_index=0)


@pytest.mark.asyncio
async def test_submit_index_out_of_range(async_db_session) -> None:
    from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
    from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    users = SQLAlchemyUserRepository(async_db_session)
    await users.create(1, None)
    questions = SQLAlchemyQuizQuestionRepository(async_db_session)
    qid = await questions.create(QuizQuestionData("q", _opts(), 0, "easy"))
    attempts = SQLAlchemyQuizAttemptRepository(async_db_session)
    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=AsyncMock(),
        leaderboard=AsyncMock(),
    )
    with pytest.raises(ValueError, match="out of range"):
        await uc.execute(telegram_id=1, question_id=qid, chosen_index=10)


@pytest.mark.asyncio
async def test_submit_success_updates_user_and_leaderboard(async_db_session) -> None:
    from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
    from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    users = SQLAlchemyUserRepository(async_db_session)
    await users.create(10, "u")
    questions = SQLAlchemyQuizQuestionRepository(async_db_session)
    qid = await questions.create(QuizQuestionData("q", _opts(), 2, "easy"))
    attempts = SQLAlchemyQuizAttemptRepository(async_db_session)
    ai = AsyncMock()
    ai.explain_quiz_choice = AsyncMock(return_value="Потому что так.")
    lb = AsyncMock()
    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=ai,
        leaderboard=lb,
    )
    att = await uc.execute(telegram_id=10, question_id=qid, chosen_index=2)
    assert att.is_correct is True
    assert att.score > 0
    lb.add_score.assert_awaited()
    refreshed = await users.get_by_telegram_id(10)
    assert refreshed is not None
    assert refreshed.score >= att.score


@pytest.mark.asyncio
async def test_submit_repeat_answer_zero_points(async_db_session) -> None:
    from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
    from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    users = SQLAlchemyUserRepository(async_db_session)
    await users.create(11, None)
    questions = SQLAlchemyQuizQuestionRepository(async_db_session)
    qid = await questions.create(QuizQuestionData("q", _opts(), 1, "easy"))
    attempts = SQLAlchemyQuizAttemptRepository(async_db_session)
    ai = AsyncMock()
    ai.explain_quiz_choice = AsyncMock(return_value="ещё раз")
    lb = AsyncMock()
    uc = SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=ai,
        leaderboard=lb,
    )
    first = await uc.execute(telegram_id=11, question_id=qid, chosen_index=1)
    assert first.score > 0
    second = await uc.execute(telegram_id=11, question_id=qid, chosen_index=1)
    assert second.score == 0
    assert "Повторный" in second.feedback
