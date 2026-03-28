from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request

from src.infrastructure.db.repositories.background_job import SQLAlchemyBackgroundJobRepository
from src.infrastructure.tasks.jobs import run_background_job


async def enqueue_background_job(
    request: Request,
    *,
    telegram_id: int,
    username: str | None,
    job_type: str,
    payload: dict[str, object],
) -> str:
    pl = dict(payload)
    if username is not None:
        pl["username"] = username
    job_id = str(uuid4())
    now = datetime.now(tz=UTC)
    factory = request.app.state.session_factory
    async with factory() as session:
        repo = SQLAlchemyBackgroundJobRepository(session)
        await repo.create_pending(
            job_id=job_id,
            telegram_id=telegram_id,
            job_type=job_type,
            payload=pl,
            created_at=now,
        )
        await session.commit()
    run_background_job.delay(job_id)
    return job_id
