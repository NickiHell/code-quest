"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from typing import Any, Self

from pydantic import AnyUrl, Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.ai_backend import AiBackend


class Settings(BaseSettings):
    """Runtime configuration (12-factor): secrets and URLs come from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    secret_key: str = Field(..., min_length=8)
    log_level: str = "INFO"

    database_url: str
    redis_url: str

    bot_token: str = Field(..., min_length=10)
    webapp_url: HttpUrl = Field(
        ...,
        description="HTTPS URL страницы Mini App (WebView внутри Telegram).",
    )
    public_base_url: HttpUrl = Field(
        ...,
        description="Корень сервера для ссылок на веб-панель и CORS.",
    )
    admin_api_key: str = Field(
        ...,
        min_length=16,
        description="Секрет для /api/admin/* (заголовок X-Admin-Key).",
    )

    ai_backend: AiBackend = Field(
        default=AiBackend.ollama,
        description="ollama | yandex_gpt | yandex_ai_studio_agent | yandex_openai_responses",
    )

    ollama_base_url: AnyUrl | None = Field(
        default=None,
        description="Базовый URL Ollama (только для ai_backend=ollama).",
    )
    ai_model: str = "qwen2.5-coder:14b"
    ai_timeout: int = Field(default=30, ge=1, le=600)

    yandex_folder_id: str | None = Field(
        default=None,
        description="YC folder ID (биллинг) для YandexGPT / AI Studio.",
    )
    yandex_auth: str | None = Field(
        default=None,
        description="API-ключ или IAM-токен Yandex Cloud (строка для SDK).",
    )
    yandex_gpt_model_name: str = Field(
        default="yandexgpt",
        description="Имя модели или полный modelUri (если содержит ://).",
    )
    yandex_gpt_model_version: str = "latest"

    yandex_assistant_id: str | None = Field(
        default=None,
        description="ID ассистента в AI Studio (ai_backend=yandex_ai_studio_agent).",
    )

    yandex_openai_base_url: str = Field(
        default="https://ai.api.cloud.yandex.net/v1",
        description="OpenAI-compatible endpoint Yandex Cloud (responses API).",
    )
    yandex_openai_model: str = Field(
        default="aliceai-llm/latest",
        description="Имя модели или полный gpt://... URI (YANDEX_CLOUD_MODEL).",
    )
    yandex_openai_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    yandex_openai_max_output_tokens: int = Field(
        default=4096,
        ge=1,
        le=32000,
        description="Лимит вывода для responses.create (MCQ JSON нужен запас).",
    )

    sandbox_timeout: int = Field(default=5, ge=1, le=300)
    sandbox_memory_limit: str = "256m"
    sandbox_network_disabled: bool = True

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure SQLAlchemy URL uses supported async drivers."""
        allowed = ("postgresql+asyncpg://", "sqlite+aiosqlite://")
        if not any(value.startswith(prefix) for prefix in allowed):
            msg = "DATABASE_URL must start with postgresql+asyncpg:// or sqlite+aiosqlite://"
            raise ValueError(msg)
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        """Accept redis:// and rediss:// URLs."""
        if not (value.startswith("redis://") or value.startswith("rediss://")):
            msg = "REDIS_URL must start with redis:// or rediss://"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def merge_yandex_cloud_env_aliases(self) -> Self:
        """Поддержка имён из доков Yandex: YANDEX_CLOUD_FOLDER, YANDEX_CLOUD_API_KEY."""
        updates: dict[str, Any] = {}
        if self.yandex_folder_id is None:
            cloud_folder = os.environ.get("YANDEX_CLOUD_FOLDER")
            if cloud_folder:
                updates["yandex_folder_id"] = cloud_folder
        if self.yandex_auth is None:
            cloud_key = os.environ.get("YANDEX_CLOUD_API_KEY")
            if cloud_key:
                updates["yandex_auth"] = cloud_key
        if self.ai_backend == AiBackend.yandex_openai_responses:
            cloud_model = os.environ.get("YANDEX_CLOUD_MODEL")
            if cloud_model:
                updates["yandex_openai_model"] = cloud_model.strip()
        if updates:
            return self.model_copy(update=updates)
        return self

    @model_validator(mode="after")
    def validate_ai_backend_fields(self) -> Self:
        """Условные обязательные поля в зависимости от AI_BACKEND."""
        if self.ai_backend == AiBackend.ollama:
            if self.ollama_base_url is None:
                msg = "OLLAMA_BASE_URL is required when AI_BACKEND=ollama"
                raise ValueError(msg)
        elif self.ai_backend == AiBackend.yandex_gpt:
            if not self.yandex_folder_id or not self.yandex_auth:
                msg = "YANDEX_FOLDER_ID and YANDEX_AUTH are required when AI_BACKEND=yandex_gpt"
                raise ValueError(msg)
        elif self.ai_backend == AiBackend.yandex_ai_studio_agent:
            if not self.yandex_folder_id or not self.yandex_auth:
                msg = (
                    "YANDEX_FOLDER_ID and YANDEX_AUTH are required when "
                    "AI_BACKEND=yandex_ai_studio_agent"
                )
                raise ValueError(msg)
            if not self.yandex_assistant_id:
                msg = "YANDEX_ASSISTANT_ID is required when AI_BACKEND=yandex_ai_studio_agent"
                raise ValueError(msg)
        elif self.ai_backend == AiBackend.yandex_openai_responses:
            if not self.yandex_folder_id or not self.yandex_auth:
                msg = (
                    "YANDEX_FOLDER_ID (или YANDEX_CLOUD_FOLDER) и YANDEX_AUTH "
                    "(или YANDEX_CLOUD_API_KEY) нужны при AI_BACKEND=yandex_openai_responses"
                )
                raise ValueError(msg)
        return self
