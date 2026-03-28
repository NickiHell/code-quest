from __future__ import annotations

import logging
from typing import assert_never

from openai import AsyncOpenAI

from src.core.ai_backend import AiBackend
from src.core.config import Settings
from src.core.interfaces.ai_provider import AbstractAIProvider
from src.infrastructure.ai.yandex_agent_service import YandexAIStudioAgentService
from src.infrastructure.ai.yandex_gpt_service import YandexGPTAIService
from src.infrastructure.ai.yandex_openai_responses_service import YandexOpenAIResponsesService

logger = logging.getLogger(__name__)


def build_provider_registry(
    settings: Settings,
    *,
    yandex_client: AsyncOpenAI | None = None,
) -> dict[AiBackend, AbstractAIProvider]:
    registry: dict[AiBackend, AbstractAIProvider] = {}

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

        if yandex_client is not None:
            try:
                registry[AiBackend.yandex_openai_responses] = (
                    YandexOpenAIResponsesService.from_settings(settings, client=yandex_client)
                )
            except Exception:
                logger.warning("yandex_openai_responses unavailable", exc_info=True)

    return registry


def create_ai_provider(
    settings: Settings,
    *,
    yandex_client: AsyncOpenAI | None = None,
) -> AbstractAIProvider:
    if settings.ai_backend == AiBackend.yandex_gpt:
        return YandexGPTAIService.from_settings(settings)

    if settings.ai_backend == AiBackend.yandex_ai_studio_agent:
        return YandexAIStudioAgentService.from_settings(settings)

    if settings.ai_backend == AiBackend.yandex_openai_responses:
        if yandex_client is None:
            msg = "yandex_client (AsyncOpenAI) is required for yandex_openai_responses backend"
            raise ValueError(msg)
        return YandexOpenAIResponsesService.from_settings(settings, client=yandex_client)

    assert_never(settings.ai_backend)
