from __future__ import annotations

import logging
from typing import Any, cast

from yandex_ai_studio_sdk import AsyncAIStudio

from src.core.config import Settings
from src.core.interfaces.ai_provider import AbstractAIProvider
from src.entities.quiz import QuizQuestionData
from src.infrastructure.ai.prompts import (
    build_evaluate_code_prompt,
    build_quiz_explain_prompt,
    build_quiz_generation_prompt,
    parse_quiz_json,
)

logger = logging.getLogger(__name__)
_MAX_ATTEMPTS = 3


class YandexGPTAIService(AbstractAIProvider):
    """YandexGPT через AsyncAIStudio.models.completions."""

    def __init__(self, *, model: Any, timeout: int) -> None:
        self._model = model
        self._timeout = timeout

    @classmethod
    def from_settings(cls, settings: Settings) -> YandexGPTAIService:
        if settings.yandex_folder_id is None or settings.yandex_auth is None:
            msg = "yandex_folder_id and yandex_auth are required"
            raise ValueError(msg)
        sdk = AsyncAIStudio(
            folder_id=settings.yandex_folder_id,
            auth=settings.yandex_auth,
        )
        model = sdk.models.completions(
            settings.yandex_gpt_model_name,
            model_version=settings.yandex_gpt_model_version,
        )
        return cls(model=model, timeout=settings.ai_timeout)

    async def _complete(self, prompt: str) -> str:
        result = await self._model.run(prompt, timeout=self._timeout)
        return cast(str, result.text)

    async def evaluate_code(self, code: str, task_description: str) -> str:
        prompt = build_evaluate_code_prompt(code, task_description)
        return await self._complete(prompt)

    async def generate_quiz_question(
        self,
        grade: str,
        topic: str | None = None,
        seen_questions: list[str] | None = None,
    ) -> QuizQuestionData:
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                prompt = build_quiz_generation_prompt(grade, topic, seen_questions)
                raw = await self._complete(prompt)
                return parse_quiz_json(raw, default_grade=grade)
            except ValueError as exc:
                last_exc = exc
                logger.warning("quiz parse attempt %d/%d failed: %s", attempt, _MAX_ATTEMPTS, exc)
        raise ValueError("quiz generation failed after retries") from last_exc

    async def explain_quiz_choice(
        self,
        question_text: str,
        options: tuple[str, ...],
        correct_index: int,
        chosen_index: int,
    ) -> str:
        prompt = build_quiz_explain_prompt(question_text, options, correct_index, chosen_index)
        return (await self._complete(prompt)).strip()
