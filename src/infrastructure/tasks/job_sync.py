from __future__ import annotations

import asyncio

from src.infrastructure.tasks.job_async import run_job_async


def run_job_sync(job_id: str, celery_task_id: str) -> None:
    asyncio.run(run_job_async(job_id, celery_task_id))
