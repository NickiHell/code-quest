"""Generic OpenAI-compatible provider (chat.completions API).

Работает с любым провайдером, реализующим OpenAI Chat Completions:
  OpenAI, Groq, Together AI, Mistral AI, Deepseek, Fireworks, Perplexity…

Нужные .env:
  AI_BACKEND=openai_compatible
  OPENAI_COMPAT_API_KEY=<ключ>
  OPENAI_COMPAT_BASE_URL=https://api.groq.com/openai/v1   # пусто = OpenAI по умолчанию
  OPENAI_COMPAT_MODEL=llama-3.3-70b-versatile
"""

from __future__ import annotations

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


class OpenAICompatService(AbstractAIProvider):
    """Делегирует вызовы любому OpenAI-совместимому эндпоинту через chat.completions."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_settings(cls, settings: Settings, *, client: AsyncOpenAI) -> OpenAICompatService:
        return cls(
            client=client,
            model=settings.openai_compat_model,
            temperature=settings.openai_compat_temperature,
            max_tokens=settings.openai_compat_max_tokens,
        )

    async def _complete(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content
        if content is None:
            msg = "OpenAI-compatible API вернул пустой ответ"
            raise ValueError(msg)
        return content

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
        raw = await self._complete(prompt)
        return parse_quiz_json(raw, default_grade=grade)

    async def explain_quiz_choice(
        self,
        question_text: str,
        options: tuple[str, ...],
        correct_index: int,
        chosen_index: int,
    ) -> str:
        prompt = build_quiz_explain_prompt(question_text, options, correct_index, chosen_index)
        return (await self._complete(prompt)).strip()
