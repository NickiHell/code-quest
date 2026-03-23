"""Доменные объекты квиза (MCQ)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class QuizQuestionData:
    """Полные данные вопроса (включая правильный индекс) — только на сервере."""

    question_text: str
    options: tuple[str, ...]
    correct_index: int
    grade: str

    def __post_init__(self) -> None:
        if not (2 <= len(self.options) <= 8):
            msg = "Quiz must have between 2 and 8 options"
            raise ValueError(msg)
        if not (0 <= self.correct_index < len(self.options)):
            msg = "correct_index out of range"
            raise ValueError(msg)


@dataclass(frozen=True)
class QuizEvaluationResult:
    """Результат проверки ответа."""

    is_correct: bool
    score: int
    feedback: str


@dataclass(frozen=True)
class QuizQuestionPublic:
    """Вопрос для клиента (без правильного индекса)."""

    id: int
    question_text: str
    options: tuple[str, ...]
    grade: str


@dataclass(frozen=True)
class QuizAttempt:
    """Сохранённая попытка."""

    id: int | None
    user_id: int
    question_id: int
    chosen_index: int
    is_correct: bool
    score: int
    feedback: str
    created_at: datetime
