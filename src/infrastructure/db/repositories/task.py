from __future__ import annotations

from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.repositories import AbstractTaskRepository
from src.entities.task import Task
from src.infrastructure.db.models.task import TaskModel


class SQLAlchemyTaskRepository(AbstractTaskRepository):
    """Task persistence via async SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, task_id: int) -> Task | None:
        """Return a task by id."""
        row = await self._session.get(TaskModel, task_id)
        return None if row is None else row.to_entity()

    async def get_daily_task(self, day: date) -> Task | None:
        """Return the task scheduled for the given calendar day."""
        stmt = select(TaskModel).where(TaskModel.daily_for == day).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else row.to_entity()

    async def list_published(self, limit: int = 50, offset: int = 0) -> list[Task]:
        """List published tasks for browsing."""
        stmt = select(TaskModel).order_by(desc(TaskModel.created_at)).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [row.to_entity() for row in rows]
