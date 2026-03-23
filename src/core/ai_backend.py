"""Режим бэкенда генерации текста (Ollama / Yandex Cloud)."""

from __future__ import annotations

from enum import StrEnum


class AiBackend(StrEnum):
    """Источник LLM для API и сценариев с ИИ."""

    ollama = "ollama"
    yandex_gpt = "yandex_gpt"
    yandex_ai_studio_agent = "yandex_ai_studio_agent"
    yandex_openai_responses = "yandex_openai_responses"
    # Любой OpenAI-совместимый провайдер: OpenAI, Groq, Together AI, Mistral, Deepseek…
    openai_compatible = "openai_compatible"
