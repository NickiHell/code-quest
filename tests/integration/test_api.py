"""Integration tests for HTTP API."""

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


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with _lifespan_client() as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_miniapp_and_admin_served() -> None:
    async with _lifespan_client() as client:
        root = await client.get("/", follow_redirects=True)
        assert root.status_code == 200
        assert "админ" in root.text.lower() or "Code Quest" in root.text

        mini = await client.get("/miniapp/")
        assert mini.status_code == 200
        assert "telegram-web-app.js" in mini.text


@pytest.mark.asyncio
async def test_admin_stats_requires_key() -> None:
    async with _lifespan_client() as client:
        response = await client.get("/api/admin/stats")
    assert response.status_code == 403
