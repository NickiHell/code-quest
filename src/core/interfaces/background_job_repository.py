from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.entities.background_job import BackgroundJob


class AbstractBackgroundJobRepository(ABC):
    @abstractmethod
    async def create_pending(
        self,
        *,
        job_id: str,
        telegram_id: int,
        job_type: str,
        payload: dict[str, object],
        created_at: datetime,
    ) -> BackgroundJob: ...

    @abstractmethod
    async def get_by_id(self, job_id: str) -> BackgroundJob | None: ...

    @abstractmethod
    async def set_running(
        self, job_id: str, *, celery_task_id: str, updated_at: datetime
    ) -> None: ...

    @abstractmethod
    async def set_succeeded(
        self,
        job_id: str,
        *,
        result: dict[str, object],
        updated_at: datetime,
    ) -> None: ...

    @abstractmethod
    async def set_failed(self, job_id: str, *, error: str, updated_at: datetime) -> None: ...
