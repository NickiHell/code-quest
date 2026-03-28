from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.exceptions import DomainError
from src.entities.background_job import BackgroundJob, BackgroundJobKind, BackgroundJobStatus
from src.entities.quiz import QuizQuestionPublic
from src.infrastructure.ai.routing_provider import RoutingAIProvider
from src.infrastructure.db.repositories.background_job import SQLAlchemyBackgroundJobRepository
from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
from src.infrastructure.db.repositories.submission import SQLAlchemySubmissionRepository
from src.infrastructure.db.repositories.task import SQLAlchemyTaskRepository
from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository
from src.infrastructure.redis.leaderboard import RedisLeaderboard
from src.infrastructure.worker_resources import worker_stack
from src.interfaces.api.schemas.quiz import QuizQuestionResponse, QuizResultResponse
from src.interfaces.api.schemas.responses import SubmissionResponse
from src.use_cases.create_submission import CreateSubmissionUseCase
from src.use_cases.next_quiz import NextQuizUseCase
from src.use_cases.submit_quiz import SubmitQuizUseCase

logger = logging.getLogger(__name__)


def _payload_int(payload: dict[str, object], key: str) -> int:
    raw = payload[key]
    if isinstance(raw, bool):
        msg = f"payload[{key!r}] must be int"
        raise TypeError(msg)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError:
            pass
    msg = f"payload[{key!r}] must be int"
    raise ValueError(msg)


def _payload_str(payload: dict[str, object], key: str) -> str:
    raw = payload[key]
    if not isinstance(raw, str):
        msg = f"payload[{key!r}] must be str"
        raise TypeError(msg)
    return raw


def _payload_str_opt(payload: dict[str, object], key: str) -> str | None:
    raw = payload.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        msg = f"payload[{key!r}] must be str or null"
        raise TypeError(msg)
    return raw


def _quiz_public_to_response(q: QuizQuestionPublic) -> dict[str, Any]:
    body = QuizQuestionResponse(
        id=q.id,
        question_number=q.question_number,
        question_text=q.question_text,
        options=list(q.options),
        grade=q.grade,
    )
    return body.model_dump(mode="json")


async def _run_dispatch(
    session: AsyncSession,
    redis: Redis,  # type: ignore[type-arg]
    ai: RoutingAIProvider,
    job: BackgroundJob,
) -> dict[str, object]:
    users = SQLAlchemyUserRepository(session)
    tasks = SQLAlchemyTaskRepository(session)
    submissions = SQLAlchemySubmissionRepository(session)
    leaderboard = RedisLeaderboard(redis)
    questions = SQLAlchemyQuizQuestionRepository(session)
    attempts = SQLAlchemyQuizAttemptRepository(session)

    telegram_id = job.telegram_id
    payload = job.payload

    if job.job_type == BackgroundJobKind.submission.value:
        task_id = _payload_int(payload, "task_id")
        code = _payload_str(payload, "code")
        submit_uc = CreateSubmissionUseCase(
            tasks=tasks,
            users=users,
            submissions=submissions,
            ai=ai,
            leaderboard=leaderboard,
        )
        entity = await submit_uc.execute(
            telegram_id=telegram_id,
            username=_payload_str_opt(payload, "username"),
            task_id=task_id,
            code=code,
        )
        if entity.id is None:
            msg = "submission persisted without id"
            raise RuntimeError(msg)
        sr = SubmissionResponse(
            id=entity.id,
            user_id=entity.user_id,
            task_id=entity.task_id,
            code=entity.code,
            feedback=entity.feedback,
            score=entity.score,
            created_at=entity.created_at,
        )
        return {"kind": BackgroundJobKind.submission.value, "data": sr.model_dump(mode="json")}

    if job.job_type == BackgroundJobKind.quiz_next.value:
        grade = _payload_str(payload, "grade")
        topic = _payload_str_opt(payload, "topic")
        next_uc = NextQuizUseCase(users=users, questions=questions, ai=ai, redis=redis)
        q = await next_uc.execute(
            telegram_id=telegram_id,
            username=_payload_str_opt(payload, "username"),
            grade=grade,
            topic=topic,
        )
        return {"kind": BackgroundJobKind.quiz_next.value, "data": _quiz_public_to_response(q)}

    if job.job_type == BackgroundJobKind.quiz_answer.value:
        question_id = _payload_int(payload, "question_id")
        chosen_index = _payload_int(payload, "chosen_index")
        answer_uc = SubmitQuizUseCase(
            users=users,
            questions=questions,
            attempts=attempts,
            ai=ai,
            leaderboard=leaderboard,
        )
        attempt = await answer_uc.execute(
            telegram_id=telegram_id,
            question_id=question_id,
            chosen_index=chosen_index,
        )
        if attempt.id is None:
            msg = "attempt without id"
            raise RuntimeError(msg)
        body = QuizResultResponse(
            attempt_id=attempt.id,
            is_correct=attempt.is_correct,
            score=attempt.score,
            feedback=attempt.feedback,
        )
        return {"kind": BackgroundJobKind.quiz_answer.value, "data": body.model_dump(mode="json")}

    msg = f"unknown job_type {job.job_type!r}"
    raise ValueError(msg)


async def run_job_async(job_id: str, celery_task_id: str) -> None:
    settings = Settings()
    async with worker_stack(settings) as (_engine, session_factory, redis, ai_service, _yc):
        now = datetime.now(tz=UTC)
        async with session_factory() as session:
            repo = SQLAlchemyBackgroundJobRepository(session)
            job = await repo.get_by_id(job_id)
            if job is None:
                logger.warning("background job %s not found", job_id)
                return
            if job.status != BackgroundJobStatus.pending.value:
                logger.info("background job %s skip status=%s", job_id, job.status)
                return
            await repo.set_running(job_id, celery_task_id=celery_task_id, updated_at=now)
            await session.commit()

        try:
            async with session_factory() as session:
                job = await SQLAlchemyBackgroundJobRepository(session).get_by_id(job_id)
                if job is None:
                    return
                result = await _run_dispatch(session, redis, ai_service, job)
                await session.commit()
        except (DomainError, TypeError, ValueError) as exc:
            logger.warning("job %s failed: %s", job_id, exc)
            async with session_factory() as session:
                repo = SQLAlchemyBackgroundJobRepository(session)
                await repo.set_failed(job_id, error=str(exc), updated_at=datetime.now(tz=UTC))
                await session.commit()
            return
        except Exception as exc:
            logger.exception("job %s unexpected error", job_id)
            async with session_factory() as session:
                repo = SQLAlchemyBackgroundJobRepository(session)
                await repo.set_failed(job_id, error=str(exc), updated_at=datetime.now(tz=UTC))
                await session.commit()
            return

        async with session_factory() as session:
            repo = SQLAlchemyBackgroundJobRepository(session)
            await repo.set_succeeded(
                job_id,
                result=result,
                updated_at=datetime.now(tz=UTC),
            )
            await session.commit()
