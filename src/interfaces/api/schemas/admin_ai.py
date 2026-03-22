"""Схемы админ-API для режима AI."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator

from src.core.ai_backend import AiBackend


class AiBackendStateResponse(BaseModel):
    """Текущий режим ИИ и список сконфигурированных бэкендов."""

    env_default: str = Field(description="Значение AI_BACKEND из окружения")
    override: str | None = Field(description="Переопределение из Redis или null")
    effective: str = Field(description="Фактически используемый бэкенд")
    available: list[str] = Field(description="Бэкенды, для которых заданы креды в .env")
    ready: bool = Field(description="Можно ли выполнять запросы к ИИ")


class AiBackendUpdateRequest(BaseModel):
    """Переключение бэкенда или сброс на значение из env."""

    backend: AiBackend | None = Field(
        default=None,
        description="Активировать один из доступных бэкендов",
    )
    clear: bool = Field(
        default=False,
        description="Сбросить override в Redis (использовать только AI_BACKEND из env)",
    )

    @model_validator(mode="after")
    def backend_or_clear(self) -> Self:
        if self.clear and self.backend is not None:
            msg = "Нельзя одновременно указывать clear и backend"
            raise ValueError(msg)
        if not self.clear and self.backend is None:
            msg = "Укажите backend или clear=true"
            raise ValueError(msg)
        return self
