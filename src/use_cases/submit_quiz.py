"""Проверка ответа MCQ, объяснение ИИ, очки и лидерборд."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.core.exceptions import NotFoundError
from src.core.interfaces.ai_provider import AbstractAIProvider, QuizEvaluator
from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.quiz_repositories import (
    AbstractQuizAttemptRepository,
    AbstractQuizQuestionRepository,
)
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.quiz import QuizAttempt, QuizEvaluationResult

logger = logging.getLogger(__name__)


class SubmitQuizUseCase:
    """Оценка выбора, сохранение попытки, обновление счёта."""

    def __init__(
        self,
        *,
        users: AbstractUserRepository,
        questions: AbstractQuizQuestionRepository,
        attempts: AbstractQuizAttemptRepository,
        ai: AbstractAIProvider,
        leaderboard: AbstractLeaderboard,
    ) -> None:
        self._users = users
        self._questions = questions
        self._attempts = attempts
        self._ai = ai
        self._leaderboard = leaderboard

    async def execute(
        self,
        *,
        telegram_id: int,
        question_id: int,
        chosen_index: int,
    ) -> QuizAttempt:
        """Проверить ответ и вернуть сохранённую попытку с фидбеком."""
        if not (0 <= chosen_index <= 9):
            msg = "chosen_index must be 0..9"
            raise ValueError(msg)

        user = await self._users.get_by_telegram_id(telegram_id)
        if user is None:
            raise NotFoundError("User not found")

        stored = await self._questions.get_by_id(question_id)
        if stored is None:
            raise NotFoundError("Question not found")

        base = QuizEvaluator.evaluate(stored.correct_index, chosen_index)
        explanation = await self._ai.explain_quiz_choice(
            stored.question_text,
            stored.options,
            stored.correct_index,
            chosen_index,
        )
        merged = QuizEvaluationResult(
            is_correct=base.is_correct,
            score=base.score,
            feedback=explanation,
        )

        attempt_id = await self._attempts.create(
            user_id=user.id,
            question_id=question_id,
            chosen_index=chosen_index,
            is_correct=merged.is_correct,
            score=merged.score,
            feedback=merged.feedback,
        )

        scored_user = user.add_score(merged.score)
        await self._users.update(scored_user)
        await self._leaderboard.add_score(user_id=user.id, points=merged.score)

        logger.info(
            "quiz attempt user=%s q=%s correct=%s score=%s",
            user.id,
            question_id,
            merged.is_correct,
            merged.score,
        )

        return QuizAttempt(
            id=attempt_id,
            user_id=user.id,
            question_id=question_id,
            chosen_index=chosen_index,
            is_correct=merged.is_correct,
            score=merged.score,
            feedback=merged.feedback,
            created_at=datetime.now(tz=UTC),
        )
