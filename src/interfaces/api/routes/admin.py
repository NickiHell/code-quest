"""Админ-API: статистика (веб-панель в браузере)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.admin.stats import fetch_admin_stats
from src.interfaces.api.deps import get_db_session, get_redis

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
