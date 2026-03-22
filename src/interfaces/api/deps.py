"""FastAPI dependency factories (composition root wiring)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.quiz_repositories import (
    AbstractQuizAttemptRepository,
    AbstractQuizQuestionRepository,
)
from src.core.interfaces.repositories import (
    AbstractSubmissionRepository,
    AbstractTaskRepository,
    AbstractUserRepository,
)
from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
from src.infrastructure.db.repositories.submission import SQLAlchemySubmissionRepository
from src.infrastructure.db.repositories.task import SQLAlchemyTaskRepository
from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository
from src.infrastructure.redis.leaderboard import RedisLeaderboard
from src.use_cases.create_submission import CreateSubmissionUseCase
from src.use_cases.leaderboard_view import LeaderboardViewUseCase
from src.use_cases.next_quiz import NextQuizUseCase
from src.use_cases.submit_quiz import SubmitQuizUseCase


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped database session with commit/rollback."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis(request: Request) -> Redis:  # type: ignore[type-arg]
    """Return the shared async Redis client."""
    return request.app.state.redis  # type: ignore[no-any-return]


async def get_ai_service(request: Request) -> AbstractAIProvider:
    """Return the configured AI provider."""
    service: AbstractAIProvider = request.app.state.ai_service
    return service


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AbstractUserRepository:
    """User repository bound to the current session."""
    return SQLAlchemyUserRepository(session)


async def get_task_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AbstractTaskRepository:
    """Task repository bound to the current session."""
    return SQLAlchemyTaskRepository(session)


async def get_submission_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AbstractSubmissionRepository:
    """Submission repository bound to the current session."""
    return SQLAlchemySubmissionRepository(session)


async def get_leaderboard(redis: Redis = Depends(get_redis)) -> AbstractLeaderboard:  # type: ignore[type-arg]
    """Redis-backed leaderboard."""
    return RedisLeaderboard(redis)


async def get_create_submission_use_case(
    tasks: AbstractTaskRepository = Depends(get_task_repository),
    users: AbstractUserRepository = Depends(get_user_repository),
    submissions: AbstractSubmissionRepository = Depends(get_submission_repository),
    ai: AbstractAIProvider = Depends(get_ai_service),
    leaderboard: AbstractLeaderboard = Depends(get_leaderboard),
) -> CreateSubmissionUseCase:
    """Orchestrator for submission creation."""
    return CreateSubmissionUseCase(
        tasks=tasks,
        users=users,
        submissions=submissions,
        ai=ai,
        leaderboard=leaderboard,
    )


async def get_quiz_question_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AbstractQuizQuestionRepository:
    """Quiz questions persistence."""
    return SQLAlchemyQuizQuestionRepository(session)


async def get_quiz_attempt_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AbstractQuizAttemptRepository:
    """Quiz attempts persistence."""
    return SQLAlchemyQuizAttemptRepository(session)


async def get_next_quiz_use_case(
    users: AbstractUserRepository = Depends(get_user_repository),
    questions: AbstractQuizQuestionRepository = Depends(get_quiz_question_repository),
    ai: AbstractAIProvider = Depends(get_ai_service),
) -> NextQuizUseCase:
    """Сгенерировать следующий вопрос."""
    return NextQuizUseCase(users=users, questions=questions, ai=ai)


async def get_submit_quiz_use_case(
    users: AbstractUserRepository = Depends(get_user_repository),
    questions: AbstractQuizQuestionRepository = Depends(get_quiz_question_repository),
    attempts: AbstractQuizAttemptRepository = Depends(get_quiz_attempt_repository),
    ai: AbstractAIProvider = Depends(get_ai_service),
    leaderboard: AbstractLeaderboard = Depends(get_leaderboard),
) -> SubmitQuizUseCase:
    """Отправка ответа на MCQ."""
    return SubmitQuizUseCase(
        users=users,
        questions=questions,
        attempts=attempts,
        ai=ai,
        leaderboard=leaderboard,
    )


async def get_leaderboard_view_use_case(
    users: AbstractUserRepository = Depends(get_user_repository),
    leaderboard: AbstractLeaderboard = Depends(get_leaderboard),
) -> LeaderboardViewUseCase:
    """Топ лидеров с именами."""
    return LeaderboardViewUseCase(users=users, leaderboard=leaderboard)
