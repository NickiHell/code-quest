from __future__ import annotations

from src.infrastructure.celery_app import celery_app
from src.infrastructure.tasks.job_sync import run_job_sync


@celery_app.task(bind=True, name="codequest.run_background_job")
def run_background_job(self: object, job_id: str) -> None:
    tid = getattr(getattr(self, "request", None), "id", None)
    run_job_sync(job_id, celery_task_id=str(tid or ""))
