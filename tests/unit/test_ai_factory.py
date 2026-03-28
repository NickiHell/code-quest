from __future__ import annotations

from unittest.mock import patch

import pytest
from openai import AsyncOpenAI

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.infrastructure.ai.factory import build_provider_registry, create_ai_provider


def _settings_with_yandex() -> Settings:
    return Settings(
        secret_key="x" * 16,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        yandex_folder_id="folder",
        yandex_auth="key",
        yandex_assistant_id="asst",
        ai_backend=AiBackend.yandex_gpt,
    )


def test_build_registry_empty_without_yandex_creds() -> None:
    # model_construct: без валидатора «нужны креды при AI_BACKEND», проверяем только ветку factory.
    s = Settings.model_construct(
        ai_backend=AiBackend.yandex_gpt,
        yandex_folder_id=None,
        yandex_auth=None,
        yandex_assistant_id=None,
    )
    assert build_provider_registry(s) == {}


def test_create_ai_provider_openai_requires_client() -> None:
    s = Settings.model_construct(
        ai_backend=AiBackend.yandex_openai_responses,
        yandex_folder_id="f",
        yandex_auth="k",
    )
    with pytest.raises(ValueError, match="yandex_client"):
        create_ai_provider(s, yandex_client=None)


@pytest.mark.asyncio
async def test_build_registry_skips_failed_providers() -> None:
    s = _settings_with_yandex()
    client = AsyncOpenAI(api_key="k", base_url="https://example.invalid/v1")
    with (
        patch(
            "src.infrastructure.ai.factory.YandexGPTAIService.from_settings",
            side_effect=RuntimeError("fail"),
        ),
        patch(
            "src.infrastructure.ai.factory.YandexAIStudioAgentService.from_settings",
            side_effect=RuntimeError("fail"),
        ),
        patch(
            "src.infrastructure.ai.factory.YandexOpenAIResponsesService.from_settings",
            side_effect=RuntimeError("fail"),
        ),
    ):
        reg = build_provider_registry(s, yandex_client=client)
    assert reg == {}
    await client.close()
