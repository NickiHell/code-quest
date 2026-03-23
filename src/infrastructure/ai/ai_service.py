"""Ollama-backed implementation of AbstractAIProvider."""

from __future__ import annotations

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.entities.quiz import QuizQuestionData
from src.infrastructure.ai.ollama_client import OllamaClient
from src.infrastructure.ai.prompts import (
    build_evaluate_code_prompt,
    build_quiz_explain_prompt,
    build_quiz_generation_prompt,
    parse_quiz_json,
)


class OllamaAIService(AbstractAIProvider):
    """Maps domain evaluation to Ollama generate prompts."""

    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    async def evaluate_code(self, code: str, task_description: str) -> str:
        """Return natural-language feedback for the submitted code."""
        prompt = build_evaluate_code_prompt(code, task_description)
        return await self._client.generate(prompt)

    async def generate_quiz_question(
        self,
        grade: str,
        topic: str | None = None,
        seen_questions: list[str] | None = None,
    ) -> QuizQuestionData:
        """Сгенерировать MCQ через строгий JSON."""
        prompt = build_quiz_generation_prompt(grade, topic, seen_questions)
        raw = await self._client.generate(prompt)
        return parse_quiz_json(raw, default_grade=grade)

    async def explain_quiz_choice(
        self,
        question_text: str,
        options: tuple[str, ...],
        correct_index: int,
        chosen_index: int,
    ) -> str:
        """Краткое объяснение по-русски."""
        prompt = build_quiz_explain_prompt(question_text, options, correct_index, chosen_index)
        return (await self._client.generate(prompt)).strip()
