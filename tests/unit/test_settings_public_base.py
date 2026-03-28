from __future__ import annotations

from src.core.config import Settings


def test_public_base_url_strips_path_to_origin() -> None:
    s = Settings.model_validate(
        {
            "secret_key": "test-secret-key-please-change",
            "database_url": "postgresql+asyncpg://u:p@h/db",
            "redis_url": "redis://localhost:6379/0",
            "bot_token": "1234567890:ABCDEF-test-token",
            "webapp_url": "https://example.com/miniapp/",
            "public_base_url": "https://example.com/miniapp/",
        },
    )
    assert str(s.public_base_url).rstrip("/") == "https://example.com"
