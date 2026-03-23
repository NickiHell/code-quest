"""Выдать следующий вопрос: генерация ИИ + сохранение."""

from __future__ import annotations

import hashlib
import logging

from redis.asyncio.client import Redis

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.quiz_repositories import AbstractQuizQuestionRepository
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.quiz import QuizQuestionData, QuizQuestionPublic

logger = logging.getLogger(__name__)

# Хранить последние N текстов вопросов на пользователя × тема × грейд (для промпта)
_SEEN_LIMIT = 40
# TTL в секундах: 7 дней
_SEEN_TTL = 7 * 24 * 3600
# Повтор генерации при совпадении хеша текста с уже выданным
_MAX_DEDUP_ATTEMPTS = 5


def _seen_key(telegram_id: int, topic: str, grade: str) -> str:
    return f"codequest:seen_qs:{telegram_id}:{topic}:{grade}"


def _seen_hash_key(telegram_id: int, topic: str, grade: str) -> str:
    return f"codequest:seen_hash:{telegram_id}:{topic}:{grade}"


def _user_seq_key(telegram_id: int) -> str:
    return f"codequest:user_q_seq:{telegram_id}"


def _question_fingerprint(text: str) -> str:
    """Нормализация + хеш для детекта повторов и перефраза с тем же смыслом."""
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


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
        await self._users.get_or_create_by_telegram_id(telegram_id, username)

        topic_key = (topic or "python").strip().lower()
        rkey = _seen_key(telegram_id, topic_key, grade)
        hkey = _seen_hash_key(telegram_id, topic_key, grade)

        raw_seen = await self._redis.lrange(rkey, 0, _SEEN_LIMIT - 1)
        seen_questions: list[str] = [
            item if isinstance(item, str) else item.decode() for item in raw_seen
        ]

        data: QuizQuestionData | None = None
        for attempt in range(_MAX_DEDUP_ATTEMPTS):
            data = await self._ai.generate_quiz_question(grade, topic, seen_questions)
            fp = _question_fingerprint(data.question_text)
            if await self._redis.sismember(hkey, fp):
                logger.info(
                    "quiz duplicate fingerprint, retry generation attempt=%s topic=%s",
                    attempt + 1,
                    topic_key,
                )
                continue
            break
        else:
            msg = "Не удалось выдать уникальный вопрос, попробуйте снова"
            raise ValueError(msg)

        seq_key = _user_seq_key(telegram_id)
        pipe = self._redis.pipeline()
        pipe.incr(seq_key)
        pipe.sadd(hkey, _question_fingerprint(data.question_text))
        pipe.expire(hkey, _SEEN_TTL)
        pipe.lpush(rkey, data.question_text)
        pipe.ltrim(rkey, 0, _SEEN_LIMIT - 1)
        pipe.expire(rkey, _SEEN_TTL)
        results = await pipe.execute()
        question_number = int(results[0])

        qid = await self._questions.create(data)
        logger.info(
            "quiz question created id=%s n=%s grade=%s topic=%s",
            qid,
            question_number,
            grade,
            topic_key,
        )
        return QuizQuestionPublic(
            id=qid,
            question_number=question_number,
            question_text=data.question_text,
            options=data.options,
            grade=data.grade,
        )
