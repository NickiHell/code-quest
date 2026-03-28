from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.infrastructure.redis.rate_limit import enforce_fixed_window_rate_limit


@pytest.mark.asyncio
async def test_enforce_skips_when_limit_non_positive() -> None:
    redis = AsyncMock()
    await enforce_fixed_window_rate_limit(
        redis,
        bucket="b",
        user_id=1,
        limit=0,
        window_seconds=60,
    )
    redis.incr.assert_not_called()


@pytest.mark.asyncio
async def test_enforce_sets_expire_on_first_hit() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    await enforce_fixed_window_rate_limit(
        redis,
        bucket="quiz_next",
        user_id=42,
        limit=5,
        window_seconds=30,
    )
    redis.incr.assert_awaited_once()
    redis.expire.assert_awaited_once_with("codequest:rl:quiz_next:42", 30)


@pytest.mark.asyncio
async def test_enforce_no_expire_when_not_first() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=3)
    await enforce_fixed_window_rate_limit(
        redis,
        bucket="x",
        user_id=1,
        limit=10,
        window_seconds=60,
    )
    redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_enforce_raises_429_when_over_limit() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=6)
    with pytest.raises(HTTPException) as exc_info:
        await enforce_fixed_window_rate_limit(
            redis,
            bucket="sub",
            user_id=9,
            limit=5,
            window_seconds=60,
        )
    assert exc_info.value.status_code == 429
