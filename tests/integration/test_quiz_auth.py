from __future__ import annotations

import pytest

from tests.integration.test_api import _lifespan_client
from tests.support.telegram_init_data import build_valid_init_data


@pytest.mark.asyncio
async def test_quiz_next_requires_init_data_header() -> None:
    async with _lifespan_client() as client:
        r = await client.post("/api/quiz/next", json={"grade": "easy", "topic": "python"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_quiz_answer_requires_init_data_header() -> None:
    async with _lifespan_client() as client:
        r = await client.post(
            "/api/quiz/answer",
            json={"question_id": 1, "chosen_index": 0},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_tasks_daily_requires_init_data_header() -> None:
    async with _lifespan_client() as client:
        r = await client.get("/api/tasks/daily")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_submissions_requires_init_data_header() -> None:
    async with _lifespan_client() as client:
        r = await client.post(
            "/api/submissions/",
            json={"task_id": 1, "code": "print(1)"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_quiz_next_rejects_tampered_init_data() -> None:
    import os

    bot = os.environ["BOT_TOKEN"]
    raw = build_valid_init_data(bot_token=bot)
    prefix = raw.rsplit("&hash=", 1)[0]
    bad = f"{prefix}&hash=deadbeef"
    async with _lifespan_client() as client:
        r = await client.post(
            "/api/quiz/next",
            json={"grade": "easy"},
            headers={"X-Telegram-Init-Data": bad},
        )
    assert r.status_code == 401
