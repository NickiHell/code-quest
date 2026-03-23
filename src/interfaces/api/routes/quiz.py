"""MCQ quiz API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.exceptions import DomainError, ExternalServiceError, NotFoundError
from src.interfaces.api.deps import (
    get_leaderboard_view_use_case,
    get_next_quiz_use_case,
    get_submit_quiz_use_case,
)
from src.interfaces.api.schemas.quiz import (
    LeaderboardEntryResponse,
    NextQuizRequest,
    QuizQuestionResponse,
    QuizResultResponse,
    SubmitQuizRequest,
)
from src.use_cases.leaderboard_view import LeaderboardViewUseCase
from src.use_cases.next_quiz import NextQuizUseCase
from src.use_cases.submit_quiz import SubmitQuizUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["quiz"])


@router.post("/quiz/next", response_model=QuizQuestionResponse, status_code=status.HTTP_201_CREATED)
async def next_question(
    body: NextQuizRequest,
    use_case: NextQuizUseCase = Depends(get_next_quiz_use_case),
) -> QuizQuestionResponse:
    """Сгенерировать и сохранить вопрос, вернуть варианты без правильного индекса."""
    try:
        q = await use_case.execute(
            telegram_id=body.telegram_id,
            username=body.username,
            grade=body.grade.value,
            topic=body.topic,
        )
    except ValueError as exc:
        logger.exception("quiz generation failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ExternalServiceError as exc:
        logger.warning("quiz AI unavailable: %s", exc.message)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    except DomainError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return QuizQuestionResponse(
        id=q.id,
        question_number=q.question_number,
        question_text=q.question_text,
        options=list(q.options),
        grade=q.grade,
    )


@router.post("/quiz/answer", response_model=QuizResultResponse)
async def submit_answer(
    body: SubmitQuizRequest,
    use_case: SubmitQuizUseCase = Depends(get_submit_quiz_use_case),
) -> QuizResultResponse:
    """Проверить выбранный вариант и начислить очки."""
    try:
        attempt = await use_case.execute(
            telegram_id=body.telegram_id,
            question_id=body.question_id,
            chosen_index=body.chosen_index,
        )
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DomainError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    if attempt.id is None:
        logger.error("attempt without id")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")

    return QuizResultResponse(
        attempt_id=attempt.id,
        is_correct=attempt.is_correct,
        score=attempt.score,
        feedback=attempt.feedback,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntryResponse])
async def quiz_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    use_case: LeaderboardViewUseCase = Depends(get_leaderboard_view_use_case),
) -> list[LeaderboardEntryResponse]:
    """Топ игроков (очки из Redis, имена из БД)."""
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
