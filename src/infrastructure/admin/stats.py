"""Сбор агрегатов для админ-панели."""

from __future__ import annotations

from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.submission import SubmissionModel
from src.infrastructure.db.models.task import TaskModel
from src.infrastructure.db.models.user import UserModel

_LEADERBOARD_KEY = "leaderboard:global"


async def fetch_admin_stats(session: AsyncSession, redis: Redis) -> dict[str, Any]:  # type: ignore[type-arg]
    """Счётчики по БД и топ лидерборда из Redis."""
    users = int(await session.scalar(select(func.count()).select_from(UserModel)) or 0)
    tasks = int(await session.scalar(select(func.count()).select_from(TaskModel)) or 0)
    submissions = int(await session.scalar(select(func.count()).select_from(SubmissionModel)) or 0)

    raw: list[tuple[str, float]] = await redis.zrevrange(
        _LEADERBOARD_KEY,
        0,
        9,
        withscores=True,
    )
    leaderboard_top = [{"user_id": int(uid), "score": int(score)} for uid, score in raw]

    return {
        "users": users,
        "tasks": tasks,
        "submissions": submissions,
        "leaderboard_top": leaderboard_top,
    }
