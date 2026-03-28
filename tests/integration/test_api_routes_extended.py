from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.core.exceptions import (
    DomainError,
    DomainValidationError,
    ExternalServiceError,
    NotFoundError,
)
from src.entities.quiz import QuizAttempt, QuizQuestionPublic
from src.entities.submission import Submission
from src.entities.task import Task
from src.entities.telegram_webapp import WebAppUser
from src.interfaces.api.deps import (
    get_create_submission_use_case,
    get_leaderboard_view_use_case,
    get_next_quiz_use_case,
    get_redis,
    get_submit_quiz_use_case,
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


@pytest.mark.asyncio
async def test_quiz_next_created() -> None:
    pub = QuizQuestionPublic(
        id=1,
        question_number=1,
        question_text="Q",
        options=tuple(f"o{i}" for i in range(5)),
        grade="easy",
    )
    uc = AsyncMock()
    uc.execute = AsyncMock(return_value=pub)

    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username="u", first_name=None, last_name=None)

    async def _nq() -> object:
        return uc

    async with _client_with_overrides(
        {
            get_webapp_user_quiz_next: _user,
            get_next_quiz_use_case: _nq,
        },
    ) as client:
        r = await client.post(
            "/api/quiz/next",
            json={"grade": "easy", "topic": "python"},
            headers=_auth_headers(),
        )
    assert r.status_code == 201
    assert r.json()["question_text"] == "Q"


@pytest.mark.asyncio
async def test_quiz_next_maps_errors() -> None:
    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username=None, first_name=None, last_name=None)

    async def _uc_val() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=ValueError("bad"))
        return m

    async def _uc_ext() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=ExternalServiceError("ai down"))
        return m

    async def _uc_dom() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=DomainError("domain"))
        return m

    async with _client_with_overrides(
        {get_webapp_user_quiz_next: _user, get_next_quiz_use_case: _uc_val},
    ) as client:
        assert (
            await client.post(
                "/api/quiz/next",
                json={"grade": "easy"},
                headers=_auth_headers(),
            )
        ).status_code == 502

    async with _client_with_overrides(
        {get_webapp_user_quiz_next: _user, get_next_quiz_use_case: _uc_ext},
    ) as client:
        assert (
            await client.post(
                "/api/quiz/next",
                json={"grade": "easy"},
                headers=_auth_headers(),
            )
        ).status_code == 503

    async with _client_with_overrides(
        {get_webapp_user_quiz_next: _user, get_next_quiz_use_case: _uc_dom},
    ) as client:
        assert (
            await client.post(
                "/api/quiz/next",
                json={"grade": "easy"},
                headers=_auth_headers(),
            )
        ).status_code == 400


@pytest.mark.asyncio
async def test_quiz_answer_flow() -> None:
    att = QuizAttempt(
        id=9,
        user_id=1,
        question_id=2,
        chosen_index=0,
        is_correct=True,
        score=2,
        feedback="ok",
        created_at=datetime.now(tz=UTC),
    )
    uc = AsyncMock()
    uc.execute = AsyncMock(return_value=att)

    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username=None, first_name=None, last_name=None)

    async def _sq() -> object:
        return uc

    async with _client_with_overrides(
        {
            get_webapp_user_quiz_answer: _user,
            get_submit_quiz_use_case: _sq,
        },
    ) as client:
        r = await client.post(
            "/api/quiz/answer",
            json={"question_id": 2, "chosen_index": 0},
            headers=_auth_headers(),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["attempt_id"] == 9
    assert body["is_correct"] is True


@pytest.mark.asyncio
async def test_quiz_answer_http_errors() -> None:
    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username=None, first_name=None, last_name=None)

    async def _nf() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=NotFoundError("nope"))
        return m

    async def _bad() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=ValueError("bad idx"))
        return m

    async def _dom() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=DomainError("d"))
        return m

    async def _no_id() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(
            return_value=QuizAttempt(
                id=None,
                user_id=1,
                question_id=1,
                chosen_index=0,
                is_correct=True,
                score=1,
                feedback="x",
                created_at=datetime.now(tz=UTC),
            ),
        )
        return m

    async with _client_with_overrides(
        {get_webapp_user_quiz_answer: _user, get_submit_quiz_use_case: _nf},
    ) as c:
        assert (
            await c.post(
                "/api/quiz/answer",
                json={"question_id": 1, "chosen_index": 0},
                headers=_auth_headers(),
            )
        ).status_code == 404

    async with _client_with_overrides(
        {get_webapp_user_quiz_answer: _user, get_submit_quiz_use_case: _bad},
    ) as c:
        assert (
            await c.post(
                "/api/quiz/answer",
                json={"question_id": 1, "chosen_index": 0},
                headers=_auth_headers(),
            )
        ).status_code == 400

    async with _client_with_overrides(
        {get_webapp_user_quiz_answer: _user, get_submit_quiz_use_case: _dom},
    ) as c:
        assert (
            await c.post(
                "/api/quiz/answer",
                json={"question_id": 1, "chosen_index": 0},
                headers=_auth_headers(),
            )
        ).status_code == 400

    async with _client_with_overrides(
        {get_webapp_user_quiz_answer: _user, get_submit_quiz_use_case: _no_id},
    ) as c:
        assert (
            await c.post(
                "/api/quiz/answer",
                json={"question_id": 1, "chosen_index": 0},
                headers=_auth_headers(),
            )
        ).status_code == 500


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
async def test_submissions_create_and_errors() -> None:
    saved = Submission(
        id=1,
        user_id=2,
        task_id=3,
        code="x",
        feedback="f",
        score=5,
        created_at=datetime.now(tz=UTC),
    )

    async def _user() -> WebAppUser:
        return WebAppUser(telegram_id=1, username=None, first_name=None, last_name=None)

    async def _ok_uc() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(return_value=saved)
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_submission: _user,
            get_create_submission_use_case: _ok_uc,
        },
    ) as c:
        r = await c.post(
            "/api/submissions/",
            json={"task_id": 3, "code": "print(1)"},
            headers=_auth_headers(),
        )
    assert r.status_code == 201

    async def _nf() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=NotFoundError("task"))
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_submission: _user,
            get_create_submission_use_case: _nf,
        },
    ) as c:
        assert (
            await c.post(
                "/api/submissions/",
                json={"task_id": 3, "code": "x"},
                headers=_auth_headers(),
            )
        ).status_code == 404

    async def _dv() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=DomainValidationError("bad"))
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_submission: _user,
            get_create_submission_use_case: _dv,
        },
    ) as c:
        assert (
            await c.post(
                "/api/submissions/",
                json={"task_id": 3, "code": "x"},
                headers=_auth_headers(),
            )
        ).status_code == 400

    async def _de() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(side_effect=DomainError("d"))
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_submission: _user,
            get_create_submission_use_case: _de,
        },
    ) as c:
        assert (
            await c.post(
                "/api/submissions/",
                json={"task_id": 3, "code": "x"},
                headers=_auth_headers(),
            )
        ).status_code == 400

    async def _noid() -> object:
        m = AsyncMock()
        m.execute = AsyncMock(
            return_value=Submission(
                id=None,
                user_id=1,
                task_id=1,
                code="c",
                feedback="f",
                score=1,
                created_at=datetime.now(tz=UTC),
            ),
        )
        return m

    async with _client_with_overrides(
        {
            get_webapp_user_submission: _user,
            get_create_submission_use_case: _noid,
        },
    ) as c:
        assert (
            await c.post(
                "/api/submissions/",
                json={"task_id": 3, "code": "x"},
                headers=_auth_headers(),
            )
        ).status_code == 500


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
