"""Репозитории квиза."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.entities.quiz import QuizQuestionData


class AbstractQuizQuestionRepository(ABC):
    """Персистентность вопросов MCQ."""

    @abstractmethod
    async def create(self, data: QuizQuestionData) -> int:
        """Сохранить вопрос, вернуть id."""

    @abstractmethod
    async def get_by_id(self, question_id: int) -> QuizQuestionData | None:
        """Загрузить вопрос по id (с correct_index)."""


class AbstractQuizAttemptRepository(ABC):
    """Персистентность попыток."""

    @abstractmethod
    async def create(
        self,
        *,
        user_id: int,
        question_id: int,
        chosen_index: int,
        is_correct: bool,
        score: int,
        feedback: str,
    ) -> int:
        """Создать запись попытки, вернуть id."""

    @abstractmethod
    async def count_attempts(self, *, user_id: int, question_id: int) -> int:
        """Сколько попыток уже было у пользователя на этот вопрос (для анти-абьюза очков)."""
