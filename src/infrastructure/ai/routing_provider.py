"""Выбор активного AI-бэкенда: env по умолчанию + опциональное переопределение в Redis."""

from __future__ import annotations

import logging

from redis.asyncio.client import Redis

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.core.interfaces.ai_provider import AbstractAIProvider
from src.entities.quiz import QuizQuestionData

logger = logging.getLogger(__name__)

REDIS_KEY_AI_BACKEND_OVERRIDE = "codequest:ai_backend_override"


class RoutingAIProvider(AbstractAIProvider):
    """Делегирует вызовы одному из зарегистрированных провайдеров по effective backend."""

    def __init__(
        self,
        settings: Settings,
        redis: Redis,  # type: ignore[type-arg]
        providers: dict[AiBackend, AbstractAIProvider],
    ) -> None:
        if not providers:
            msg = "Нет доступных AI-провайдеров — проверьте .env (Ollama, Yandex и т.д.)."
            raise ValueError(msg)
        self._settings = settings
        self._redis = redis
        self._providers = providers

    @property
    def providers(self) -> dict[AiBackend, AbstractAIProvider]:
        return self._providers

    async def _effective_backend(self) -> AiBackend:
        raw = await self._redis.get(REDIS_KEY_AI_BACKEND_OVERRIDE)
        if raw:
            try:
                chosen = AiBackend(str(raw).strip())
                if chosen in self._providers:
                    return chosen
                logger.warning(
                    "override AI backend %s недоступен (нет клиента), используем env",
                    raw,
                )
            except ValueError:
                logger.warning("некорректное значение в Redis для AI backend: %s", raw)

        default = self._settings.ai_backend
        if default not in self._providers:
            msg = (
                f"AI backend по умолчанию ({default.value}) не сконфигурирован. "
                f"Доступны: {[b.value for b in self._providers]}"
            )
            raise RuntimeError(msg)
        return default

    async def describe_runtime(self) -> dict[str, object]:
        """Состояние для админки: дефолт из env, override в Redis, эффективный режим."""
        available = sorted(b.value for b in self._providers)
        raw = await self._redis.get(REDIS_KEY_AI_BACKEND_OVERRIDE)
        override: str | None = None
        if raw:
            s = str(raw).strip()
            try:
                b = AiBackend(s)
                if b in self._providers:
                    override = s
            except ValueError:
                override = None
        try:
            eff = await self._effective_backend()
            effective = eff.value
            ready = True
        except RuntimeError:
            effective = ""
            ready = False
        return {
            "env_default": self._settings.ai_backend.value,
            "override": override,
            "effective": effective,
            "available": available,
            "ready": ready,
        }

    async def evaluate_code(self, code: str, task_description: str) -> str:
        backend = await self._effective_backend()
        return await self._providers[backend].evaluate_code(code, task_description)

    async def generate_quiz_question(
        self,
        grade: str,
        topic: str | None = None,
    ) -> QuizQuestionData:
        backend = await self._effective_backend()
        return await self._providers[backend].generate_quiz_question(grade, topic)

    async def explain_quiz_choice(
        self,
        question_text: str,
        options: tuple[str, ...],
        correct_index: int,
        chosen_index: int,
    ) -> str:
        backend = await self._effective_backend()
        return await self._providers[backend].explain_quiz_choice(
            question_text,
            options,
            correct_index,
            chosen_index,
        )
