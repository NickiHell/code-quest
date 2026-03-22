"""Unit tests for application use cases."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest

from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.repositories import (
    AbstractSubmissionRepository,
    AbstractTaskRepository,
    AbstractUserRepository,
)
from src.entities.submission import Submission
from src.entities.task import Task
from src.entities.user import User
from src.use_cases.create_submission import CreateSubmissionUseCase
from src.use_cases.evaluate_code import EvaluateCodeUseCase


@pytest.mark.asyncio
async def test_evaluate_code_delegates_to_ai(mock_ai_service: AbstractAIProvider) -> None:
    use_case = EvaluateCodeUseCase(mock_ai_service)
    result = await use_case.execute("print(1)", "Print one")
    assert result == "Excellent solution."
    mock_ai_service.evaluate_code.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_submission_persists_and_updates_leaderboard() -> None:
    task = Task(
        id=1,
        title="Daily",
        description="Implement hello world",
        difficulty="easy",
        daily_for=date.today(),
        created_at=datetime.now(tz=UTC),
    )

    tasks = AsyncMock(spec=AbstractTaskRepository)
    tasks.get_by_id = AsyncMock(return_value=task)

    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_telegram_id = AsyncMock(return_value=None)
    users.create = AsyncMock(
        return_value=User(
            id=1,
            telegram_id=42,
            username="tester",
            created_at=datetime.now(tz=UTC),
            score=0,
        ),
    )
    users.update = AsyncMock(side_effect=lambda u: u)

    submissions = AsyncMock(spec=AbstractSubmissionRepository)
    submissions.create = AsyncMock(
        return_value=Submission(
            id=10,
            user_id=1,
            task_id=1,
            code="print('hi')",
            feedback="Excellent solution.",
            score=10,
            created_at=datetime.now(tz=UTC),
        ),
    )

    ai = AsyncMock()
    ai.evaluate_code = AsyncMock(return_value="Excellent solution.")

    leaderboard = AsyncMock(spec=AbstractLeaderboard)
    leaderboard.add_score = AsyncMock()

    use_case = CreateSubmissionUseCase(
        tasks=tasks,
        users=users,
        submissions=submissions,
        ai=ai,
        leaderboard=leaderboard,
    )

    result = await use_case.execute(
        telegram_id=42,
        username="tester",
        task_id=1,
        code="print('hi')",
    )

    assert result.id == 10
    leaderboard.add_score.assert_awaited_once_with(user_id=1, points=10)
