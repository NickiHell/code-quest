"""Тесты LeaderboardViewUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.user import User
from src.use_cases.leaderboard_view import LeaderboardViewUseCase


@pytest.mark.asyncio
async def test_leaderboard_view_batches_user_fetch() -> None:
    leaderboard = AsyncMock(spec=AbstractLeaderboard)
    leaderboard.top = AsyncMock(return_value=[(10, 100), (20, 50)])

    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_ids = AsyncMock(
        return_value={
            10: User(
                id=10,
                telegram_id=1,
                username="a",
                created_at=datetime.now(tz=UTC),
                score=100,
            ),
            20: User(
                id=20,
                telegram_id=2,
                username="b",
                created_at=datetime.now(tz=UTC),
                score=50,
            ),
        },
    )

    uc = LeaderboardViewUseCase(users=users, leaderboard=leaderboard)
    rows = await uc.execute(limit=10)

    users.get_by_ids.assert_awaited_once_with([10, 20])
    assert len(rows) == 2
    assert rows[0].rank == 1 and rows[0].user_id == 10
    assert rows[1].rank == 2 and rows[1].user_id == 20
