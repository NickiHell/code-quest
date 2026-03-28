from __future__ import annotations

import pytest

from src.core.config import Settings


@pytest.mark.parametrize(
    ("public_base_url", "expected_origin"),
    [
        ("https://example.com/miniapp/", "https://example.com"),
        ("https://api.example.com/v1/foo", "https://api.example.com"),
        ("https://example.com", "https://example.com"),
    ],
)
def test_public_base_url_strips_path_to_origin(
    public_base_url: str,
    expected_origin: str,
) -> None:
    s = Settings.model_validate(
        {
            "secret_key": "test-secret-key-please-change",
            "database_url": "postgresql+asyncpg://u:p@h/db",
            "redis_url": "redis://localhost:6379/0",
            "bot_token": "1234567890:ABCDEF-test-token",
            "webapp_url": "https://example.com/miniapp/",
            "public_base_url": public_base_url,
            "telegram_webhook_secret": "0123456789abcdef",
        },
    )
    assert str(s.public_base_url).rstrip("/") == expected_origin
