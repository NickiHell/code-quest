"""User ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.entities.user import User
from src.infrastructure.db.models.base import Base


class UserModel(Base):
    """Persistent representation of a Telegram user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def to_entity(self) -> User:
        """Map ORM row to a domain entity."""
        return User(
            id=self.id,
            telegram_id=int(self.telegram_id),
            username=self.username,
            created_at=self.created_at,
            score=self.score,
        )
