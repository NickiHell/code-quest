"""Режим LLM: только Yandex Cloud."""

from __future__ import annotations

from enum import StrEnum


class AiBackend(StrEnum):
    yandex_gpt = "yandex_gpt"
    yandex_ai_studio_agent = "yandex_ai_studio_agent"
    yandex_openai_responses = "yandex_openai_responses"
