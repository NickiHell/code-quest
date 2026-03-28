from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.entities.quiz import QuizAttempt
from src.infrastructure.db.models.base import Base


class QuizAttemptModel(Base):
    """Ответ пользователя и результат."""

    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chosen_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> QuizAttempt:
        """Доменная сущность."""
        return QuizAttempt(
            id=self.id,
            user_id=self.user_id,
            question_id=self.question_id,
            chosen_index=self.chosen_index,
            is_correct=self.is_correct,
            score=self.score,
            feedback=self.feedback,
            created_at=self.created_at,
        )
