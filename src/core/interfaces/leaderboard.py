"""Leaderboard persistence port (Redis-backed implementation in infrastructure)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractLeaderboard(ABC):
    """Ordered ranking by score."""

    @abstractmethod
    async def add_score(self, user_id: int, points: int) -> None:
        """Increment the user's total score in the leaderboard."""

    @abstractmethod
    async def top(self, limit: int = 10) -> list[tuple[int, int]]:
        """Return (user_id, score) pairs, highest score first."""
