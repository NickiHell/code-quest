"""Выдать следующий вопрос: генерация ИИ + сохранение."""

from __future__ import annotations

import logging

from redis.asyncio.client import Redis

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.quiz_repositories import AbstractQuizQuestionRepository
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.quiz import QuizQuestionPublic

logger = logging.getLogger(__name__)

# Хранить последние N вопросов на пользователя × тема × грейд
_SEEN_LIMIT = 10
# TTL в секундах: 7 дней
_SEEN_TTL = 7 * 24 * 3600


def _seen_key(telegram_id: int, topic: str, grade: str) -> str:
    return f"codequest:seen_qs:{telegram_id}:{topic}:{grade}"


class NextQuizUseCase:
    """Создаёт пользователя при необходимости, генерирует и сохраняет вопрос."""

    def __init__(
        self,
        *,
        users: AbstractUserRepository,
        questions: AbstractQuizQuestionRepository,
        ai: AbstractAIProvider,
        redis: Redis,  # type: ignore[type-arg]
    ) -> None:
        self._users = users
        self._questions = questions
        self._ai = ai
        self._redis = redis

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

        topic_key = (topic or "python").strip().lower()
        rkey = _seen_key(telegram_id, topic_key, grade)

        # Загрузить последние N вопросов из Redis
        raw_seen: list = await self._redis.lrange(rkey, 0, _SEEN_LIMIT - 1)
        seen_questions: list[str] = [
            item if isinstance(item, str) else item.decode() for item in raw_seen
        ]

        data = await self._ai.generate_quiz_question(grade, topic, seen_questions)

        # Сохранить новый вопрос в начало списка
        pipe = self._redis.pipeline()
        pipe.lpush(rkey, data.question_text)
        pipe.ltrim(rkey, 0, _SEEN_LIMIT - 1)
        pipe.expire(rkey, _SEEN_TTL)
        await pipe.execute()

        qid = await self._questions.create(data)
        logger.info("quiz question created id=%s grade=%s topic=%s", qid, grade, topic_key)
        return QuizQuestionPublic(
            id=qid,
            question_text=data.question_text,
            options=data.options,
            grade=data.grade,
        )
