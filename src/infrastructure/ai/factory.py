"""Фабрика провайдера ИИ по настройкам."""

from __future__ import annotations

import logging

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

logger = logging.getLogger(__name__)


def build_provider_registry(
    settings: Settings,
    *,
    httpx_client: httpx.AsyncClient | None,
    openai_client: AsyncOpenAI | None,
) -> dict[AiBackend, AbstractAIProvider]:
    """Собрать провайдеры по .env (несколько бэкендов — переключение в рантайме)."""
    registry: dict[AiBackend, AbstractAIProvider] = {}

    if httpx_client is not None and settings.ollama_base_url is not None:
        try:
            ollama = OllamaClient(httpx_client, settings.ai_model)
            registry[AiBackend.ollama] = OllamaAIService(ollama)
        except Exception:
            logger.exception("failed to register ollama backend")

    if settings.yandex_folder_id and settings.yandex_auth:
        try:
            registry[AiBackend.yandex_gpt] = YandexGPTAIService.from_settings(settings)
        except Exception:
            logger.warning("yandex_gpt unavailable", exc_info=True)

        if settings.yandex_assistant_id:
            try:
                agent = YandexAIStudioAgentService.from_settings(settings)
                registry[AiBackend.yandex_ai_studio_agent] = agent
            except Exception:
                logger.warning("yandex_ai_studio_agent unavailable", exc_info=True)

        if openai_client is not None:
            try:
                yor = YandexOpenAIResponsesService.from_settings(
                    settings,
                    client=openai_client,
                )
                registry[AiBackend.yandex_openai_responses] = yor
            except Exception:
                logger.warning("yandex_openai_responses unavailable", exc_info=True)

    return registry


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
