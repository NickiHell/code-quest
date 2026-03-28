from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.redis.leaderboard import RedisLeaderboard


@pytest.mark.asyncio
async def test_add_score_calls_zincrby() -> None:
    redis = AsyncMock()
    lb = RedisLeaderboard(redis)
    await lb.add_score(user_id=7, points=3)
    redis.zincrby.assert_awaited_once_with("leaderboard:global", 3.0, "7")


@pytest.mark.asyncio
async def test_top_empty_when_limit_non_positive() -> None:
    redis = AsyncMock()
    lb = RedisLeaderboard(redis)
    assert await lb.top(limit=0) == []
    redis.zrevrange.assert_not_called()


@pytest.mark.asyncio
async def test_top_maps_scores() -> None:
    redis = AsyncMock()
    redis.zrevrange = AsyncMock(
        return_value=[("10", 100.0), ("2", 5.0)],
    )
    lb = RedisLeaderboard(redis)
    rows = await lb.top(limit=2)
    assert rows == [(10, 100), (2, 5)]
    redis.zrevrange.assert_awaited_once_with(
        "leaderboard:global",
        0,
        1,
        withscores=True,
    )
