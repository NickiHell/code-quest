"""Фабрика провайдера ИИ по настройкам."""

from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.core.interfaces.ai_provider import AbstractAIProvider
from src.infrastructure.ai.ai_service import OllamaAIService
from src.infrastructure.ai.ollama_client import OllamaClient
from src.infrastructure.ai.yandex_agent_service import YandexAIStudioAgentService
from src.infrastructure.ai.yandex_gpt_service import YandexGPTAIService
from src.infrastructure.ai.yandex_openai_responses_service import YandexOpenAIResponsesService


def create_ai_provider(
    settings: Settings,
    *,
    httpx_client: httpx.AsyncClient | None,
    openai_client: AsyncOpenAI | None = None,
) -> AbstractAIProvider:
    """Собрать реализацию AbstractAIProvider (Ollama или Yandex)."""
    if settings.ai_backend == AiBackend.ollama:
        if httpx_client is None:
            msg = "httpx_client is required for ollama backend"
            raise ValueError(msg)
        assert settings.ollama_base_url is not None
        ollama = OllamaClient(httpx_client, settings.ai_model)
        return OllamaAIService(ollama)

    if settings.ai_backend == AiBackend.yandex_gpt:
        return YandexGPTAIService.from_settings(settings)

    if settings.ai_backend == AiBackend.yandex_ai_studio_agent:
        return YandexAIStudioAgentService.from_settings(settings)

    if settings.ai_backend == AiBackend.yandex_openai_responses:
        if openai_client is None:
            msg = "openai_client is required for yandex_openai_responses backend"
            raise ValueError(msg)
        return YandexOpenAIResponsesService.from_settings(settings, client=openai_client)

    msg = f"Unsupported AI backend: {settings.ai_backend}"
    raise ValueError(msg)
