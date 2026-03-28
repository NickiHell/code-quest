from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@asynccontextmanager
async def _lifespan_client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


_EXPECTED_HEALTH_KEYS = frozenset({"status", "version", "postgres", "redis"})


@pytest.mark.asyncio
async def test_health_endpoint_schema_and_semantics() -> None:
    async with _lifespan_client() as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert frozenset(payload.keys()) == _EXPECTED_HEALTH_KEYS
    assert payload["version"] == "0.1.0"
    assert payload["postgres"] == "ok"
    assert payload["redis"] in ("ok", "unavailable")
    if payload["redis"] == "ok":
        assert payload["status"] == "ok"
    else:
        assert payload["status"] == "degraded"


@pytest.mark.parametrize("path", ["/", "/miniapp/"])
@pytest.mark.asyncio
async def test_miniapp_static_serves_web_app_script(path: str) -> None:
    async with _lifespan_client() as client:
        r = await client.get(path, follow_redirects=True)
    assert r.status_code == 200
    assert "telegram-web-app.js" in r.text
    assert "text/html" in r.headers.get("content-type", "")
