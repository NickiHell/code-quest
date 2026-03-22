"""User aggregate (pure data)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    """Application user identified by Telegram."""

    id: int
    telegram_id: int
    username: str | None
    created_at: datetime
    score: int = 0

    def add_score(self, points: int) -> User:
        """Return a new instance with an updated score."""
        return User(
            id=self.id,
            telegram_id=self.telegram_id,
            username=self.username,
            created_at=self.created_at,
            score=self.score + points,
        )
