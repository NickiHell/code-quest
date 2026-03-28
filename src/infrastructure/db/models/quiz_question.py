from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.entities.quiz import QuizQuestionData
from src.infrastructure.db.models.base import Base


class QuizQuestionModel(Base):
    """Хранение вопроса с секретным correct_index."""

    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_domain(self) -> QuizQuestionData:
        """Конвертация в доменный объект."""
        opts = tuple(str(x) for x in self.options)
        return QuizQuestionData(
            question_text=self.question_text,
            options=opts,
            correct_index=int(self.correct_index),
            grade=self.grade,
        )
