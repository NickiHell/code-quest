from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status

from src.entities.telegram_webapp import WebAppUser
from src.infrastructure.db.repositories.background_job import SQLAlchemyBackgroundJobRepository
from src.interfaces.api.deps import get_background_job_repo, get_webapp_user
from src.interfaces.api.schemas.jobs import JobStatusResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_VALID_JOB_STATUS = frozenset({"pending", "running", "succeeded", "failed"})


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    web_user: WebAppUser = Depends(get_webapp_user),
    repo: SQLAlchemyBackgroundJobRepository = Depends(get_background_job_repo),
) -> JobStatusResponse:
    row = await repo.get_by_id(job_id)
    if row is None or row.telegram_id != web_user.telegram_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    st = row.status
    if st not in _VALID_JOB_STATUS:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="bad job status")
    status_lit = cast(
        Literal["pending", "running", "succeeded", "failed"],
        st,
    )
    return JobStatusResponse(
        job_id=row.id,
        status=status_lit,
        result=row.result,
        error=row.error,
    )
