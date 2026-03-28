from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.entities.task import Task
from src.entities.telegram_webapp import WebAppUser
from src.interfaces.api.deps import (
    get_leaderboard_view_use_case,
    get_redis,
    get_task_repository,
    get_user_repository,
    get_webapp_user_quiz_answer,
    get_webapp_user_quiz_next,
    get_webapp_user_submission,
    get_webapp_user_tasks_daily,
)
from src.main import create_app
from src.use_cases.leaderboard_view import LeaderboardRow
from tests.support.telegram_init_data import build_valid_init_data


def _auth_headers() -> dict[str, str]:
    raw = build_valid_init_data(bot_token=os.environ["BOT_TOKEN"])
    return {"X-Telegram-Init-Data": raw}


def _mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.ping = AsyncMock(return_value=True)
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock(return_value=True)
    r.get = AsyncMock(return_value=None)
    r.set = AsyncMock(return_value=True)
    r.delete = AsyncMock(return_value=1)
    r.zrevrange = AsyncMock(return_value=[])
    pipe = MagicMock()
    pipe.incr = MagicMock()
    pipe.sadd = MagicMock()
    pipe.expire = MagicMock()
    pipe.lpush = MagicMock()
    pipe.ltrim = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, True, True, 1, True, True])
    r.pipeline = MagicMock(return_value=pipe)
    return r


@asynccontextmanager
async def _client_with_overrides(
    overrides: dict[Callable[..., Any], Callable[..., Any]] | None = None,
) -> AsyncIterator[AsyncClient]:
    app = create_app()
    mock_redis = _mock_redis()
    app.dependency_overrides[get_redis] = lambda: mock_redis
    for dep, fn in (overrides or {}).items():
        app.dependency_overrides[dep] = fn
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("path", "user_dep", "json_body"),
    [
        (
            "/api/quiz/next",
            get_webapp_user_quiz_next,
            {"grade": "easy", "topic": "python"},
        ),
        (
            "/api/quiz/answer",
            get_webapp_user_quiz_answer,
            {"question_id": 2, "chosen_index": 0},
        ),
    ],
)
@pytest.mark.asyncio
async def test_quiz_async_returns_202_enqueues_job(
    path: str,
    user_dep: Callable[..., Any],
    json_body: dict[str, object],
) -> None:
    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username="u", first_name=None, last_name=None)

    with patch("src.interfaces.api.job_enqueue.run_background_job") as m_task:
        m_task.delay = MagicMock()
        async with _client_with_overrides({user_dep: _user}) as client:
            r = await client.post(path, json=json_body, headers=_auth_headers())
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body
    assert body["status_url"] == f"/api/jobs/{body['job_id']}"
    m_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_leaderboard_ok() -> None:
    rows = [
        LeaderboardRow(rank=1, user_id=1, telegram_id=10, username="a", score=5),
    ]
    uc = AsyncMock()
    uc.execute = AsyncMock(return_value=rows)

    async def _lb() -> object:
        return uc

    async with _client_with_overrides({get_leaderboard_view_use_case: _lb}) as client:
        r = await client.get("/api/leaderboard?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["score"] == 5


@pytest.mark.asyncio
async def test_submissions_202_and_empty_code_400() -> None:
    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username=None, first_name=None, last_name=None)

    with patch("src.interfaces.api.job_enqueue.run_background_job") as m_task:
        m_task.delay = MagicMock()
        async with _client_with_overrides({get_webapp_user_submission: _user}) as c:
            r = await c.post(
                "/api/submissions/",
                json={"task_id": 3, "code": "print(1)"},
                headers=_auth_headers(),
            )
    assert r.status_code == 202
    m_task.delay.assert_called_once()

    async with _client_with_overrides({get_webapp_user_submission: _user}) as c:
        bad = await c.post(
            "/api/submissions/",
            json={"task_id": 3, "code": "   "},
            headers=_auth_headers(),
        )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_tasks_daily_and_users_me() -> None:
    task = Task(
        id=1,
        title="T",
        description="D",
        difficulty="easy",
        daily_for=datetime.now(tz=UTC).date(),
        created_at=datetime.now(tz=UTC),
    )

    async def _wu() -> WebAppUser:
        return WebAppUser(telegram_id=1, username=None, first_name=None, last_name=None)

    async def _repo() -> object:
        m = AsyncMock()
        m.get_daily_task = AsyncMock(return_value=task)
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_tasks_daily: _wu,
            get_task_repository: _repo,
        },
    ) as c:
        r = await c.get("/api/tasks/daily", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["title"] == "T"

    async def _repo_none() -> object:
        m = AsyncMock()
        m.get_daily_task = AsyncMock(return_value=None)
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_tasks_daily: _wu,
            get_task_repository: _repo_none,
        },
    ) as c:
        assert (await c.get("/api/tasks/daily", headers=_auth_headers())).status_code == 404

    from src.entities.user import User

    u = User(
        id=5,
        telegram_id=99,
        username="n",
        created_at=datetime.now(tz=UTC),
        score=3,
    )

    async def _urepo() -> object:
        m = AsyncMock()
        m.get_by_telegram_id = AsyncMock(return_value=u)
        return m

    async with _client_with_overrides({get_user_repository: _urepo}) as c:
        r = await c.get("/api/users/me?telegram_id=99")
    assert r.status_code == 200
    assert r.json()["score"] == 3

    async def _urepo_none() -> object:
        m = AsyncMock()
        m.get_by_telegram_id = AsyncMock(return_value=None)
        return m

    async with _client_with_overrides({get_user_repository: _urepo_none}) as c:
        assert (await c.get("/api/users/me?telegram_id=1")).status_code == 404
