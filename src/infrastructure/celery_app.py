from __future__ import annotations

from celery import Celery

from src.core.config import celery_broker_url_from_environ

celery_app = Celery(
    "codequest",
    broker=celery_broker_url_from_environ(),
    backend=None,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_default_queue="codequest",
)

import src.infrastructure.tasks.jobs  # noqa: E402, F401
