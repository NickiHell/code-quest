from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.infrastructure.sandbox.docker_runner import DockerSandboxRunner


def _minimal_settings() -> Settings:
    return Settings(
        secret_key="x" * 16,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        ai_backend=AiBackend.yandex_gpt,
    )


@pytest.mark.asyncio
async def test_run_python_snippet_uses_stub_and_closes_client() -> None:
    fake_client = MagicMock()
    with patch("docker.from_env", return_value=fake_client):
        runner = DockerSandboxRunner(_minimal_settings())
        out = await runner.run_python_snippet("print(1)")
    assert out == "sandbox-not-implemented"
    fake_client.close.assert_called_once()
