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
from src.infrastructure.ai.openai_compat_service import OpenAICompatService
from src.infrastructure.ai.yandex_agent_service import YandexAIStudioAgentService
from src.infrastructure.ai.yandex_gpt_service import YandexGPTAIService
from src.infrastructure.ai.yandex_openai_responses_service import YandexOpenAIResponsesService

logger = logging.getLogger(__name__)


def build_provider_registry(
    settings: Settings,
    *,
    yandex_client: AsyncOpenAI | None = None,
    openai_compat_client: AsyncOpenAI | None = None,
    httpx_client: httpx.AsyncClient | None = None,
) -> dict[AiBackend, AbstractAIProvider]:
    """Собрать все доступные провайдеры; переключение бэкенда — в рантайме через Redis."""
    registry: dict[AiBackend, AbstractAIProvider] = {}

    # Ollama (опционально — для локальной разработки)
    if httpx_client is not None and settings.ollama_base_url is not None:
        try:
            ollama = OllamaClient(httpx_client, settings.ai_model)
            registry[AiBackend.ollama] = OllamaAIService(ollama)
        except Exception:
            logger.exception("failed to register ollama backend")

    # YandexGPT через yandex-ai-studio-sdk
    if settings.yandex_folder_id and settings.yandex_auth:
        try:
            registry[AiBackend.yandex_gpt] = YandexGPTAIService.from_settings(settings)
        except Exception:
            logger.warning("yandex_gpt unavailable", exc_info=True)

        if settings.yandex_assistant_id:
            try:
                registry[AiBackend.yandex_ai_studio_agent] = (
                    YandexAIStudioAgentService.from_settings(settings)
                )
            except Exception:
                logger.warning("yandex_ai_studio_agent unavailable", exc_info=True)

        if yandex_client is not None:
            try:
                registry[AiBackend.yandex_openai_responses] = (
                    YandexOpenAIResponsesService.from_settings(settings, client=yandex_client)
                )
            except Exception:
                logger.warning("yandex_openai_responses unavailable", exc_info=True)

    # Любой OpenAI-совместимый провайдер (OpenAI, Groq, Together AI, Mistral, Deepseek…)
    if openai_compat_client is not None and settings.openai_compat_api_key:
        try:
            registry[AiBackend.openai_compatible] = OpenAICompatService.from_settings(
                settings, client=openai_compat_client
            )
        except Exception:
            logger.warning("openai_compatible unavailable", exc_info=True)

    return registry


def create_ai_provider(
    settings: Settings,
    *,
    yandex_client: AsyncOpenAI | None = None,
    openai_compat_client: AsyncOpenAI | None = None,
    httpx_client: httpx.AsyncClient | None = None,
) -> AbstractAIProvider:
    """Собрать одну реализацию AbstractAIProvider по AI_BACKEND из настроек."""
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
        if yandex_client is None:
            msg = "yandex_client (AsyncOpenAI) is required for yandex_openai_responses backend"
            raise ValueError(msg)
        return YandexOpenAIResponsesService.from_settings(settings, client=yandex_client)

    if settings.ai_backend == AiBackend.openai_compatible:
        if openai_compat_client is None:
            msg = "openai_compat_client (AsyncOpenAI) is required for openai_compatible backend"
            raise ValueError(msg)
        return OpenAICompatService.from_settings(settings, client=openai_compat_client)

    msg = f"Unsupported AI backend: {settings.ai_backend}"
    raise ValueError(msg)
