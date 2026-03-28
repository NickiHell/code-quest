from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.entities.user import User
from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository


@pytest.mark.asyncio
async def test_get_or_create_retries_after_integrity_error() -> None:
    session = AsyncMock()
    repo = SQLAlchemyUserRepository(session)
    existing = User(
        id=3,
        telegram_id=99,
        username="u",
        created_at=datetime.now(tz=UTC),
        score=0,
    )
    with (
        patch.object(
            repo,
            "get_by_telegram_id",
            new=AsyncMock(side_effect=[None, existing]),
        ),
        patch.object(
            repo,
            "create",
            new=AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("dup"))),
        ),
    ):
        out = await repo.get_or_create_by_telegram_id(99, "u")
    assert out is existing
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_reraises_when_user_still_missing() -> None:
    session = AsyncMock()
    repo = SQLAlchemyUserRepository(session)
    with (
        patch.object(repo, "get_by_telegram_id", new=AsyncMock(return_value=None)),
        patch.object(
            repo,
            "create",
            new=AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("dup"))),
        ),
        pytest.raises(IntegrityError),
    ):
        await repo.get_or_create_by_telegram_id(7, "n")
    session.rollback.assert_awaited_once()
