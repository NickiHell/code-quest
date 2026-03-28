from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.entities.task import Task
from src.infrastructure.db.models.base import Base


class TaskModel(Base):
    """Published programming task."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    daily_for: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> Task:
        """Map ORM row to domain Task."""
        return Task(
            id=self.id,
            title=self.title,
            description=self.description,
            difficulty=self.difficulty,
            daily_for=self.daily_for,
            created_at=self.created_at,
        )
