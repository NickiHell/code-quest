from __future__ import annotations

import os
from typing import Any, Self
from urllib.parse import ParseResult, urlparse, urlunparse

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.ai_backend import AiBackend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    secret_key: str = Field(..., min_length=8)
    log_level: str = "INFO"
    log_dir: str = Field(default="logs")

    database_url: str
    database_url_direct: str | None = None
    redis_url: str
    celery_broker_url: str | None = None

    bot_token: str = Field(..., min_length=10)

    telegram_webhook_secret: str = Field(..., min_length=16)
    telegram_set_webhook_on_startup: bool = Field(default=True)
    telegram_init_data_max_age_seconds: int = Field(default=86400, ge=0, le=604800)
    rate_limit_quiz_next_per_minute: int = Field(default=10, ge=1)
    rate_limit_quiz_answer_per_minute: int = Field(default=60, ge=1)
    rate_limit_submissions_per_minute: int = Field(default=15, ge=1)
    webapp_url: HttpUrl = Field(...)
    public_base_url: HttpUrl = Field(...)

    ai_backend: AiBackend = Field(default=AiBackend.yandex_openai_responses)
    ai_timeout: int = Field(default=30, ge=1, le=600)

    yandex_folder_id: str | None = None
    yandex_auth: str | None = None
    yandex_gpt_model_name: str = "yandexgpt"
    yandex_gpt_model_version: str = "latest"

    yandex_assistant_id: str | None = None

    yandex_openai_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    yandex_openai_model: str = "aliceai-llm/latest"
    yandex_openai_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    yandex_openai_max_output_tokens: int = Field(default=4096, ge=1, le=32000)

    sandbox_timeout: int = Field(default=5, ge=1, le=300)
    sandbox_memory_limit: str = "256m"
    sandbox_network_disabled: bool = True

    @field_validator("public_base_url", mode="before")
    @classmethod
    def public_base_must_be_origin(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value
        s = value.strip()
        if not s.startswith(("http://", "https://")):
            return value
        parsed = urlparse(s)
        if not parsed.netloc:
            return value
        if parsed.path not in ("", "/"):
            return f"{parsed.scheme}://{parsed.netloc}"
        return s.rstrip("/") or value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        allowed = ("postgresql+asyncpg://", "sqlite+aiosqlite://")
        if not any(value.startswith(prefix) for prefix in allowed):
            msg = "DATABASE_URL must start with postgresql+asyncpg:// or sqlite+aiosqlite://"
            raise ValueError(msg)
        return value

    @field_validator("database_url_direct", mode="before")
    @classmethod
    def empty_database_url_direct_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url_direct")
    @classmethod
    def validate_database_url_direct(cls, value: str | None) -> str | None:
        if value is None:
            return None
        allowed = ("postgresql+asyncpg://", "sqlite+aiosqlite://")
        if not any(value.startswith(prefix) for prefix in allowed):
            msg = "DATABASE_URL_DIRECT must start with postgresql+asyncpg:// or sqlite+aiosqlite://"
            raise ValueError(msg)
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            msg = "REDIS_URL must start with redis:// or rediss://"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def merge_yandex_cloud_env_aliases(self) -> Self:
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
    def default_celery_broker(self) -> Self:
        if self.celery_broker_url is not None:
            return self
        return self.model_copy(
            update={"celery_broker_url": _redis_url_with_db_index(self.redis_url, 1)},
        )

    @model_validator(mode="after")
    def validate_ai_backend_fields(self) -> Self:
        if self.ai_backend == AiBackend.yandex_gpt:
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
        elif self.ai_backend == AiBackend.yandex_openai_responses and (
            not self.yandex_folder_id or not self.yandex_auth
        ):
            msg = (
                "YANDEX_FOLDER_ID (или YANDEX_CLOUD_FOLDER) и YANDEX_AUTH "
                "(или YANDEX_CLOUD_API_KEY) нужны при AI_BACKEND=yandex_openai_responses"
            )
            raise ValueError(msg)
        return self


def _redis_url_with_db_index(redis_url: str, db_index: int) -> str:
    parsed: ParseResult = urlparse(redis_url)
    return urlunparse(parsed._replace(path=f"/{db_index}"))


def celery_broker_url_from_environ() -> str:
    """URL брокера Celery из env без конструирования Settings (ранний import)."""
    explicit = os.environ.get("CELERY_BROKER_URL", "").strip()
    if explicit:
        return explicit
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        msg = "REDIS_URL or CELERY_BROKER_URL must be set for Celery"
        raise ValueError(msg)
    return _redis_url_with_db_index(redis_url, 1)


def migration_database_url(settings: Settings) -> str:
    return str(settings.database_url_direct or settings.database_url)
