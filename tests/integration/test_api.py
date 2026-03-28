from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
import redis.asyncio as redis_async
import redis.exceptions as redis_exceptions
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import create_app


async def _redis_available() -> bool:
    url = os.environ.get("REDIS_URL", "")
    if not url.startswith(("redis://", "rediss://")):
        return False
    client = redis_async.from_url(url, decode_responses=True)
    try:
        return await client.ping() is True
    except (TimeoutError, OSError, redis_exceptions.ConnectionError):
        return False
    finally:
        await client.aclose()


@asynccontextmanager
async def _lifespan_client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with _lifespan_client() as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "0.1.0"
    assert payload["postgres"] == "ok"
    assert payload["redis"] in ("ok", "unavailable")
    if payload["redis"] == "ok":
        assert payload["status"] == "ok"
    else:
        assert payload["status"] == "degraded"


@pytest.mark.asyncio
async def test_root_redirects_to_miniapp() -> None:
    async with _lifespan_client() as client:
        root = await client.get("/", follow_redirects=True)
        assert root.status_code == 200
        assert "telegram-web-app.js" in root.text

        mini = await client.get("/miniapp/")
        assert mini.status_code == 200
        assert "telegram-web-app.js" in mini.text
