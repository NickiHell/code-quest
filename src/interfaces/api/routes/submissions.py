from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.exceptions import DomainError, DomainValidationError, NotFoundError
from src.entities.telegram_webapp import WebAppUser
from src.interfaces.api.deps import get_create_submission_use_case, get_webapp_user_submission
from src.interfaces.api.schemas.requests import CreateSubmissionRequest
from src.interfaces.api.schemas.responses import SubmissionResponse
from src.use_cases.create_submission import CreateSubmissionUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    body: CreateSubmissionRequest,
    web_user: WebAppUser = Depends(get_webapp_user_submission),
    use_case: CreateSubmissionUseCase = Depends(get_create_submission_use_case),
) -> SubmissionResponse:
    """Accept a new submission, run AI evaluation, persist results."""
    try:
        entity = await use_case.execute(
            telegram_id=web_user.telegram_id,
            username=web_user.username,
            task_id=body.task_id,
            code=body.code,
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except DomainValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except DomainError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    if entity.id is None:
        logger.error("submission persisted without id")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")

    return SubmissionResponse(
        id=entity.id,
        user_id=entity.user_id,
        task_id=entity.task_id,
        code=entity.code,
        feedback=entity.feedback,
        score=entity.score,
        created_at=entity.created_at,
    )
