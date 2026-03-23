"""Фабрика ИИ."""

from __future__ import annotations

import httpx
import pytest

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.infrastructure.ai.ai_service import OllamaAIService
from src.infrastructure.ai.factory import create_ai_provider


@pytest.mark.asyncio
async def test_factory_ollama_uses_ollama_service() -> None:
    settings = Settings(
        ai_backend=AiBackend.ollama,
        ollama_base_url="http://localhost:11434",  # type: ignore[arg-type]
    )
    assert settings.ai_backend == AiBackend.ollama
    async with httpx.AsyncClient(base_url="http://localhost:11434") as client:
        svc = create_ai_provider(settings, httpx_client=client)
        assert isinstance(svc, OllamaAIService)


def test_factory_ollama_requires_client() -> None:
    settings = Settings(
        ai_backend=AiBackend.ollama,
        ollama_base_url="http://localhost:11434",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="httpx_client"):
        create_ai_provider(settings, httpx_client=None)


def test_factory_openai_compat_requires_client() -> None:
    settings = Settings(
        ai_backend=AiBackend.openai_compatible,
        openai_compat_api_key="sk-test",
    )
    with pytest.raises(ValueError, match="openai_compat_client"):
        create_ai_provider(settings, openai_compat_client=None)
