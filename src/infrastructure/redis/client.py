from __future__ import annotations

from redis.asyncio.client import Redis


def create_redis_client(url: str) -> Redis:  # type: ignore[type-arg]
    """Create a decode-responses async Redis client."""
    return Redis.from_url(url, decode_responses=True)
