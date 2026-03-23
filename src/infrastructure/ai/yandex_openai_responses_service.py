"""Yandex Cloud через OpenAI-совместимый API (responses.create на ai.api.cloud.yandex.net)."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

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


class YandexOpenAIResponsesService(AbstractAIProvider):
    """Как в примере Yandex: AsyncOpenAI + project=folder + model gpt://folder/..."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model_uri: str,
        temperature: float,
        max_output_tokens: int,
    ) -> None:
        self._client = client
        self._model_uri = model_uri
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        client: AsyncOpenAI,
    ) -> YandexOpenAIResponsesService:
        assert settings.yandex_folder_id is not None
        model = settings.yandex_openai_model.strip()
        model_uri = model if "://" in model else f"gpt://{settings.yandex_folder_id}/{model}"
        return cls(
            client=client,
            model_uri=model_uri,
            temperature=settings.yandex_openai_temperature,
            max_output_tokens=settings.yandex_openai_max_output_tokens,
        )

    async def _complete(self, prompt: str) -> str:
        response = await self._client.responses.create(
            model=self._model_uri,
            temperature=self._temperature,
            instructions="",
            input=prompt,
            max_output_tokens=self._max_output_tokens,
        )
        return response.output_text

    async def evaluate_code(self, code: str, task_description: str) -> str:
        prompt = build_evaluate_code_prompt(code, task_description)
        return await self._complete(prompt)

    async def generate_quiz_question(
        self,
        grade: str,
        topic: str | None = None,
        seen_questions: list[str] | None = None,
    ) -> QuizQuestionData:
        prompt = build_quiz_generation_prompt(grade, topic, seen_questions)
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
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
