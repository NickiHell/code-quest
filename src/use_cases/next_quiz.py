"""Выдать следующий вопрос: генерация ИИ + сохранение."""

from __future__ import annotations

import logging

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.quiz_repositories import AbstractQuizQuestionRepository
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.quiz import QuizQuestionPublic

logger = logging.getLogger(__name__)


class NextQuizUseCase:
    """Создаёт пользователя при необходимости, генерирует и сохраняет вопрос."""

    def __init__(
        self,
        *,
        users: AbstractUserRepository,
        questions: AbstractQuizQuestionRepository,
        ai: AbstractAIProvider,
    ) -> None:
        self._users = users
        self._questions = questions
        self._ai = ai

    async def execute(
        self,
        *,
        telegram_id: int,
        username: str | None,
        grade: str,
        topic: str | None = None,
    ) -> QuizQuestionPublic:
        """Сгенерировать MCQ и вернуть публичную форму без correct_index."""
        user = await self._users.get_by_telegram_id(telegram_id)
        if user is None:
            await self._users.create(telegram_id, username)

        data = await self._ai.generate_quiz_question(grade, topic)
        qid = await self._questions.create(data)
        logger.info("quiz question created id=%s grade=%s", qid, grade)
        return QuizQuestionPublic(
            id=qid,
            question_text=data.question_text,
            options=data.options,
            grade=data.grade,
        )
