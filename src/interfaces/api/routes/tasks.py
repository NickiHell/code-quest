"""Task HTTP routes."""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.interfaces.repositories import AbstractTaskRepository
from src.interfaces.api.deps import get_task_repository
from src.interfaces.api.schemas.responses import TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/daily", response_model=TaskResponse)
async def get_daily_task(
    repo: AbstractTaskRepository = Depends(get_task_repository),
    day: date | None = Query(
        default=None,
        description="Calendar day (defaults to today in UTC).",
    ),
) -> TaskResponse:
    """Return the programming task scheduled for the day."""
    target = day if day is not None else datetime.now(tz=UTC).date()
    task = await repo.get_daily_task(target)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No daily task for this date")
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        difficulty=task.difficulty,
        daily_for=task.daily_for,
        created_at=task.created_at,
    )
