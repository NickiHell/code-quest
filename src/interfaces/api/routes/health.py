from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from redis.asyncio.client import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.interfaces.api.deps import get_db_session, get_redis
from src.interfaces.api.schemas.responses import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> HealthResponse:
    """Liveness/readiness: проверка PostgreSQL и Redis."""
    version = "0.1.0"
    pg = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("health: postgres check failed: %s", exc)
        pg = "unavailable"

    rd = "ok"
    try:
        pong = await redis.ping()
        if pong is not True:
            rd = "unavailable"
    except Exception as exc:
        logger.warning("health: redis check failed: %s", exc)
        rd = "unavailable"

    overall = "ok" if pg == "ok" and rd == "ok" else "degraded"
    return HealthResponse(status=overall, version=version, postgres=pg, redis=rd)
