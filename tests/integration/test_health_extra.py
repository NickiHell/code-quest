from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.interfaces.api.deps import get_db_session, get_redis
from src.main import create_app


async def _bad_db_session() -> AsyncGenerator[AsyncMock]:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise


@pytest.mark.asyncio
async def test_health_degraded_when_postgres_check_fails() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = _bad_db_session

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["postgres"] == "unavailable"
    assert body["status"] == "degraded"
    assert body["redis"] in ("ok", "unavailable")


@pytest.mark.parametrize(
    "ping_impl",
    [
        AsyncMock(side_effect=OSError("no redis")),
        AsyncMock(return_value=None),
    ],
)
@pytest.mark.asyncio
async def test_health_degraded_when_redis_unhealthy(ping_impl: AsyncMock) -> None:
    app = create_app()

    async def _redis() -> AsyncMock:
        r = AsyncMock()
        r.ping = ping_impl
        return r

    app.dependency_overrides[get_redis] = _redis

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["redis"] == "unavailable"
    assert body["status"] == "degraded"
