from __future__ import annotations

from fastapi import HTTPException, status
from redis.asyncio.client import Redis


async def enforce_fixed_window_rate_limit(
    redis: Redis,  # type: ignore[type-arg]
    *,
    bucket: str,
    user_id: int,
    limit: int,
    window_seconds: int,
) -> None:
    """
    Увеличить счётчик в окне window_seconds; при превышении limit — HTTP 429.

    redis: redis.asyncio.Redis с decode_responses=True (или совместимый INCR/EXPIRE).
    """
    if limit <= 0:
        return
    key = f"codequest:rl:{bucket}:{user_id}"
    n = await redis.incr(key)
    if n == 1:
        await redis.expire(key, window_seconds)
    if n > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Подождите минуту и попробуйте снова.",
        )
