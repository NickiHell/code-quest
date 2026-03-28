from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.entities.submission import Submission
from src.infrastructure.db.models.base import Base


class SubmissionModel(Base):
    """Stored submission with AI feedback."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> Submission:
        """Map ORM row to domain Submission."""
        return Submission(
            id=self.id,
            user_id=self.user_id,
            task_id=self.task_id,
            code=self.code,
            feedback=self.feedback,
            score=self.score,
            created_at=self.created_at,
        )
