from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.core.exceptions import DomainValidationError, NotFoundError
from src.use_cases.create_submission import CreateSubmissionUseCase, _score_from_feedback


def test_score_from_feedback_heuristic() -> None:
    assert _score_from_feedback("This is incorrect") == 0
    assert _score_from_feedback("Excellent work") == 10
    assert _score_from_feedback("OK") == 5


@pytest.mark.asyncio
async def test_execute_rejects_blank_code(async_db_session) -> None:
    from src.infrastructure.db.repositories.submission import SQLAlchemySubmissionRepository
    from src.infrastructure.db.repositories.task import SQLAlchemyTaskRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    uc = CreateSubmissionUseCase(
        tasks=SQLAlchemyTaskRepository(async_db_session),
        users=SQLAlchemyUserRepository(async_db_session),
        submissions=SQLAlchemySubmissionRepository(async_db_session),
        ai=AsyncMock(),
        leaderboard=AsyncMock(),
    )
    with pytest.raises(DomainValidationError):
        await uc.execute(telegram_id=1, username=None, task_id=1, code="   \n")


@pytest.mark.asyncio
async def test_execute_task_not_found(async_db_session) -> None:
    from src.infrastructure.db.repositories.submission import SQLAlchemySubmissionRepository
    from src.infrastructure.db.repositories.task import SQLAlchemyTaskRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    uc = CreateSubmissionUseCase(
        tasks=SQLAlchemyTaskRepository(async_db_session),
        users=SQLAlchemyUserRepository(async_db_session),
        submissions=SQLAlchemySubmissionRepository(async_db_session),
        ai=AsyncMock(),
        leaderboard=AsyncMock(),
    )
    with pytest.raises(NotFoundError, match="Task"):
        await uc.execute(telegram_id=1, username=None, task_id=99, code="x")


@pytest.mark.asyncio
async def test_execute_persists_and_scores(async_db_session) -> None:
    from src.infrastructure.db.models.task import TaskModel
    from src.infrastructure.db.repositories.submission import SQLAlchemySubmissionRepository
    from src.infrastructure.db.repositories.task import SQLAlchemyTaskRepository
    from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository

    async_db_session.add(
        TaskModel(
            title="T",
            description="Do X",
            difficulty="easy",
            daily_for=None,
            created_at=datetime.now(tz=UTC),
        ),
    )
    await async_db_session.flush()
    tid = int((await async_db_session.execute(select(TaskModel.id).limit(1))).scalar_one())

    ai = AsyncMock()
    ai.evaluate_code = AsyncMock(return_value="Excellent solution.")
    lb = AsyncMock()
    uc = CreateSubmissionUseCase(
        tasks=SQLAlchemyTaskRepository(async_db_session),
        users=SQLAlchemyUserRepository(async_db_session),
        submissions=SQLAlchemySubmissionRepository(async_db_session),
        ai=ai,
        leaderboard=lb,
    )
    out = await uc.execute(telegram_id=50, username="x", task_id=tid, code="print(1)")
    assert out.id is not None
    assert out.score == 10
    lb.add_score.assert_awaited()
