"""Фабрика ИИ."""

from __future__ import annotations

import pytest

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.infrastructure.ai.factory import create_ai_provider


def _minimal_settings(**kwargs: object) -> Settings:
    base = {
        "secret_key": "test-secret-key-please-change",
        "database_url": "postgresql+asyncpg://u:p@h/db",
        "redis_url": "redis://localhost:6379/0",
        "bot_token": "1234567890:ABCDEF-test-token",
        "webapp_url": "https://example.com/miniapp/",
        "public_base_url": "https://example.com",
        "admin_api_key": "test-admin-key-for-ci-16",
    }
    base.update(kwargs)
    return Settings.model_validate(base)


def test_factory_yandex_openai_requires_client() -> None:
    settings = _minimal_settings(
        ai_backend=AiBackend.yandex_openai_responses,
        yandex_folder_id="b1",
        yandex_auth="key",
    )
    with pytest.raises(ValueError, match="yandex_client"):
        create_ai_provider(settings, yandex_client=None)
