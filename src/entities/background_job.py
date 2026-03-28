from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BackgroundJobKind(StrEnum):
    submission = "submission"
    quiz_next = "quiz_next"
    quiz_answer = "quiz_answer"


class BackgroundJobStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


@dataclass(frozen=True)
class BackgroundJob:
    id: str
    telegram_id: int
    job_type: str
    status: str
    payload: dict[str, object]
    result: dict[str, object] | None
    error: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime
