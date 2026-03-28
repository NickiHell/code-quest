from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.background_job_repository import AbstractBackgroundJobRepository
from src.entities.background_job import BackgroundJob, BackgroundJobStatus
from src.infrastructure.db.models.background_job import BackgroundJobModel


class SQLAlchemyBackgroundJobRepository(AbstractBackgroundJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, row: BackgroundJobModel) -> BackgroundJob:
        return BackgroundJob(
            id=row.id,
            telegram_id=int(row.telegram_id),
            job_type=row.job_type,
            status=row.status,
            payload=dict(row.payload),
            result=dict(row.result) if row.result is not None else None,
            error=row.error,
            celery_task_id=row.celery_task_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_pending(
        self,
        *,
        job_id: str,
        telegram_id: int,
        job_type: str,
        payload: dict[str, object],
        created_at: datetime,
    ) -> BackgroundJob:
        row = BackgroundJobModel(
            id=job_id,
            telegram_id=telegram_id,
            job_type=job_type,
            status=BackgroundJobStatus.pending.value,
            payload=payload,
            result=None,
            error=None,
            celery_task_id=None,
            created_at=created_at,
            updated_at=created_at,
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_entity(row)

    async def get_by_id(self, job_id: str) -> BackgroundJob | None:
        row = await self._session.get(BackgroundJobModel, job_id)
        return None if row is None else self._to_entity(row)

    async def set_running(self, job_id: str, *, celery_task_id: str, updated_at: datetime) -> None:
        row = await self._session.get(BackgroundJobModel, job_id)
        if row is None:
            return
        row.status = BackgroundJobStatus.running.value
        row.celery_task_id = celery_task_id
        row.updated_at = updated_at

    async def set_succeeded(
        self,
        job_id: str,
        *,
        result: dict[str, object],
        updated_at: datetime,
    ) -> None:
        row = await self._session.get(BackgroundJobModel, job_id)
        if row is None:
            return
        row.status = BackgroundJobStatus.succeeded.value
        row.result = result
        row.error = None
        row.updated_at = updated_at

    async def set_failed(self, job_id: str, *, error: str, updated_at: datetime) -> None:
        row = await self._session.get(BackgroundJobModel, job_id)
        if row is None:
            return
        row.status = BackgroundJobStatus.failed.value
        row.error = error
        row.updated_at = updated_at
