"""AI evaluation port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.entities.quiz import QuizEvaluationResult, QuizQuestionData


class AbstractAIProvider(ABC):
    """Abstraction over LLM-backed tasks."""

    @abstractmethod
    async def evaluate_code(self, code: str, task_description: str) -> str:
        """Return natural-language feedback for the submitted code."""

    @abstractmethod
    async def generate_quiz_question(
        self,
        grade: str,
        topic: str | None = None,
        seen_questions: list[str] | None = None,
    ) -> QuizQuestionData:
        """Сгенерировать вопрос с ровно 10 вариантами и корректным индексом."""

    @abstractmethod
    async def explain_quiz_choice(
        self,
        question_text: str,
        options: tuple[str, ...],
        correct_index: int,
        chosen_index: int,
    ) -> str:
        """Краткое объяснение для UX после выбора (правильно/неправильно)."""


class QuizEvaluator:
    """Чистая логика очков (без сети)."""

    @staticmethod
    def evaluate(
        correct_index: int,
        chosen_index: int,
        *,
        points_correct: int = 10,
        points_wrong: int = 0,
    ) -> QuizEvaluationResult:
        """Детерминированная оценка совпадения индексов."""
        is_correct = chosen_index == correct_index
        score = points_correct if is_correct else points_wrong
        return QuizEvaluationResult(
            is_correct=is_correct,
            score=score,
            feedback="",
        )
