"""DTO для MCQ API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Grade(StrEnum):
    """Грейд кандидата."""

    junior = "junior"
    middle = "middle"
    senior = "senior"


class NextQuizRequest(BaseModel):
    """Запрос нового вопроса."""

    telegram_id: int = Field(..., ge=1)
    username: str | None = Field(default=None, max_length=255)
    grade: Grade
    topic: str | None = Field(default=None, max_length=200)


class QuizQuestionResponse(BaseModel):
    """Вопрос без правильного индекса."""

    id: int
    question_number: int = Field(
        ...,
        ge=1,
        description="Персональный порядковый номер для пользователя",
    )
    question_text: str
    options: list[str]
    grade: str


class SubmitQuizRequest(BaseModel):
    """Ответ на вопрос."""

    telegram_id: int = Field(..., ge=1)
    question_id: int = Field(..., ge=1)
    chosen_index: int = Field(..., ge=0, le=4)


class QuizResultResponse(BaseModel):
    """Результат проверки."""

    attempt_id: int
    is_correct: bool
    score: int
    feedback: str


class LeaderboardEntryResponse(BaseModel):
    """Строка лидерборда."""

    rank: int
    user_id: int
    telegram_id: int
    username: str | None
    score: int
