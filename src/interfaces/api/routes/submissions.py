from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.entities.background_job import BackgroundJobKind
from src.entities.telegram_webapp import WebAppUser
from src.interfaces.api.deps import get_webapp_user_submission
from src.interfaces.api.job_enqueue import enqueue_background_job
from src.interfaces.api.schemas.jobs import JobAcceptedResponse
from src.interfaces.api.schemas.requests import CreateSubmissionRequest

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("/", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_submission(
    body: CreateSubmissionRequest,
    request: Request,
    web_user: WebAppUser = Depends(get_webapp_user_submission),
) -> JobAcceptedResponse:
    if not body.code.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Code must not be empty")
    job_id = await enqueue_background_job(
        request,
        telegram_id=web_user.telegram_id,
        username=web_user.username,
        job_type=BackgroundJobKind.submission.value,
        payload={"task_id": body.task_id, "code": body.code},
    )
    return JobAcceptedResponse(job_id=job_id, status_url=f"/api/jobs/{job_id}")
