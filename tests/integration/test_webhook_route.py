from __future__ import annotations

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.mark.asyncio
async def test_telegram_webhook_wrong_secret_returns_404() -> None:
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/webhook/telegram/not-the-secret",
                json={"update_id": 1},
            )
    assert r.status_code == 404
