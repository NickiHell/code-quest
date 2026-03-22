"""Админ-API: статистика (веб-панель в браузере)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.admin.stats import fetch_admin_stats
from src.infrastructure.ai.routing_provider import REDIS_KEY_AI_BACKEND_OVERRIDE, RoutingAIProvider
from src.interfaces.api.deps import get_db_session, get_redis
from src.interfaces.api.schemas.admin_ai import AiBackendStateResponse, AiBackendUpdateRequest

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_admin(
    request: Request,
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
) -> None:
    """Проверка секрета админ-панели."""
    settings = request.app.state.settings
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/stats")
async def admin_stats(
    _: None = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> dict[str, object]:
    """Сводка по пользователям, задачам, отправкам и лидерборду."""
    return await fetch_admin_stats(session, redis)


@router.get("/ai-backend", response_model=AiBackendStateResponse)
async def get_ai_backend(
    request: Request,
    _: None = Depends(require_admin),
) -> AiBackendStateResponse:
    """Текущий AI-бэкенд: дефолт из env, опциональный override в Redis, список доступных."""
    router = cast_ai_router(request)
    data = await router.describe_runtime()
    return AiBackendStateResponse.model_validate(data)


@router.put("/ai-backend", response_model=AiBackendStateResponse)
async def put_ai_backend(
    request: Request,
    body: AiBackendUpdateRequest,
    _: None = Depends(require_admin),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> AiBackendStateResponse:
    """Переключить активный бэкенд (Redis) или сбросить на AI_BACKEND из env."""
    router = cast_ai_router(request)
    available = router.providers.keys()
    if body.clear:
        await redis.delete(REDIS_KEY_AI_BACKEND_OVERRIDE)
    else:
        assert body.backend is not None
        if body.backend not in available:
            names = ", ".join(sorted(b.value for b in available))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Бэкенд недоступен: {body.backend.value}. Сконфигурированы: {names or 'none'}"
                ),
            )
        await redis.set(REDIS_KEY_AI_BACKEND_OVERRIDE, body.backend.value)
    data = await router.describe_runtime()
    return AiBackendStateResponse.model_validate(data)


def cast_ai_router(request: Request) -> RoutingAIProvider:
    """Достаёт RoutingAIProvider из состояния приложения."""
    raw = request.app.state.ai_service
    if not isinstance(raw, RoutingAIProvider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI router is not configured",
        )
    return raw
