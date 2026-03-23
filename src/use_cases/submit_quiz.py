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

_REPEAT_NO_POINTS_SUFFIX = "\n\n— Повторный ответ на этот вопрос не начисляет очки в зачёт."


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
        if chosen_index < 0:
            msg = "chosen_index must be non-negative"
            raise ValueError(msg)

        user = await self._users.get_by_telegram_id(telegram_id)
        if user is None:
            raise NotFoundError("User not found")

        stored = await self._questions.get_by_id(question_id)
        if stored is None:
            raise NotFoundError("Question not found")

        n_opts = len(stored.options)
        if not (0 <= chosen_index < n_opts):
            msg = "chosen_index out of range for this question"
            raise ValueError(msg)

        prior_attempts = await self._attempts.count_attempts(
            user_id=user.id,
            question_id=question_id,
        )
        already_answered = prior_attempts > 0

        base = QuizEvaluator.evaluate(stored.correct_index, chosen_index, stored.grade)
        explanation = await self._ai.explain_quiz_choice(
            stored.question_text,
            stored.options,
            stored.correct_index,
            chosen_index,
        )
        effective_score = 0 if already_answered else base.score
        feedback = explanation + _REPEAT_NO_POINTS_SUFFIX if already_answered else explanation
        merged = QuizEvaluationResult(
            is_correct=base.is_correct,
            score=effective_score,
            feedback=feedback,
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
            "quiz attempt user=%s q=%s correct=%s score=%s repeat=%s",
            user.id,
            question_id,
            merged.is_correct,
            merged.score,
            already_answered,
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
