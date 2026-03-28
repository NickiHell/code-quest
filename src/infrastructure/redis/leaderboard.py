from __future__ import annotations

from redis.asyncio.client import Redis

from src.core.interfaces.leaderboard import AbstractLeaderboard

_LEADERBOARD_KEY = "leaderboard:global"


class RedisLeaderboard(AbstractLeaderboard):
    """Stores cumulative scores in a ZSET."""

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def add_score(self, user_id: int, points: int) -> None:
        """Increment the user's total score in the leaderboard."""
        await self._redis.zincrby(_LEADERBOARD_KEY, float(points), str(user_id))

    async def top(self, limit: int = 10) -> list[tuple[int, int]]:
        """Return (user_id, score) pairs, highest score first."""
        if limit <= 0:
            return []
        raw: list[tuple[str, float]] = await self._redis.zrevrange(
            _LEADERBOARD_KEY,
            0,
            max(limit - 1, 0),
            withscores=True,
        )
        return [(int(uid), int(score)) for uid, score in raw]
