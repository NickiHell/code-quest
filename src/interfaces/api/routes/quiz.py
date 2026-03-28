from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from src.entities.background_job import BackgroundJobKind
from src.entities.telegram_webapp import WebAppUser
from src.interfaces.api.deps import (
    get_leaderboard_view_use_case,
    get_webapp_user_quiz_answer,
    get_webapp_user_quiz_next,
)
from src.interfaces.api.job_enqueue import enqueue_background_job
from src.interfaces.api.schemas.jobs import JobAcceptedResponse
from src.interfaces.api.schemas.quiz import (
    LeaderboardEntryResponse,
    NextQuizRequest,
    SubmitQuizRequest,
)
from src.use_cases.leaderboard_view import LeaderboardViewUseCase

router = APIRouter(prefix="/api", tags=["quiz"])


@router.post("/quiz/next", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def next_question(
    body: NextQuizRequest,
    request: Request,
    web_user: WebAppUser = Depends(get_webapp_user_quiz_next),
) -> JobAcceptedResponse:
    job_id = await enqueue_background_job(
        request,
        telegram_id=web_user.telegram_id,
        username=web_user.username,
        job_type=BackgroundJobKind.quiz_next.value,
        payload={
            "grade": body.grade.value,
            "topic": body.topic,
        },
    )
    return JobAcceptedResponse(job_id=job_id, status_url=f"/api/jobs/{job_id}")


@router.post(
    "/quiz/answer",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_answer(
    body: SubmitQuizRequest,
    request: Request,
    web_user: WebAppUser = Depends(get_webapp_user_quiz_answer),
) -> JobAcceptedResponse:
    job_id = await enqueue_background_job(
        request,
        telegram_id=web_user.telegram_id,
        username=web_user.username,
        job_type=BackgroundJobKind.quiz_answer.value,
        payload={
            "question_id": body.question_id,
            "chosen_index": body.chosen_index,
        },
    )
    return JobAcceptedResponse(job_id=job_id, status_url=f"/api/jobs/{job_id}")


@router.get("/leaderboard", response_model=list[LeaderboardEntryResponse])
async def quiz_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    use_case: LeaderboardViewUseCase = Depends(get_leaderboard_view_use_case),
) -> list[LeaderboardEntryResponse]:
    rows = await use_case.execute(limit=limit)
    return [
        LeaderboardEntryResponse(
            rank=r.rank,
            user_id=r.user_id,
            telegram_id=r.telegram_id,
            username=r.username,
            score=r.score,
        )
        for r in rows
    ]
