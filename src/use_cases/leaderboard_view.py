"""Сборка топа Redis + профили пользователей."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.repositories import AbstractUserRepository


@dataclass(frozen=True)
class LeaderboardRow:
    """Строка таблицы лидеров."""

    rank: int
    user_id: int
    telegram_id: int
    username: str | None
    score: int


class LeaderboardViewUseCase:
    """Обогащает ZSET идентификаторами Telegram."""

    def __init__(
        self,
        *,
        users: AbstractUserRepository,
        leaderboard: AbstractLeaderboard,
    ) -> None:
        self._users = users
        self._leaderboard = leaderboard

    async def execute(self, *, limit: int = 10) -> list[LeaderboardRow]:
        """Вернуть топ с именами (если пользователь найден)."""
        raw = await self._leaderboard.top(limit=limit)
        rows: list[LeaderboardRow] = []
        for rank, (uid, score) in enumerate(raw, start=1):
            user = await self._users.get_by_id(uid)
            rows.append(
                LeaderboardRow(
                    rank=rank,
                    user_id=uid,
                    telegram_id=user.telegram_id if user else 0,
                    username=user.username if user else None,
                    score=score,
                ),
            )
        return rows
