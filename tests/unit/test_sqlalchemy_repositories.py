from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from src.entities.quiz import QuizQuestionData
from src.entities.submission import Submission
from src.infrastructure.db.models.task import TaskModel
from src.infrastructure.db.repositories.quiz_attempt import SQLAlchemyQuizAttemptRepository
from src.infrastructure.db.repositories.quiz_question import SQLAlchemyQuizQuestionRepository
from src.infrastructure.db.repositories.submission import SQLAlchemySubmissionRepository
from src.infrastructure.db.repositories.task import SQLAlchemyTaskRepository
from src.infrastructure.db.repositories.user import SQLAlchemyUserRepository


def _opts() -> tuple[str, str, str, str, str]:
    return tuple(f"o{i}" for i in range(5))


@pytest.mark.asyncio
async def test_user_repo_crud_and_list_top(async_db_session) -> None:
    repo = SQLAlchemyUserRepository(async_db_session)
    u1 = await repo.create(telegram_id=1, username="a")
    u2 = await repo.create(telegram_id=2, username="b")
    assert await repo.get_by_id(u1.id) == u1
    assert await repo.get_by_telegram_id(2) == u2
    assert await repo.get_by_ids([]) == {}
    by_ids = await repo.get_by_ids([u1.id, u2.id, 999])
    assert set(by_ids) == {u1.id, u2.id}

    updated = await repo.update(u1.add_score(10))
    assert updated.score == 10
    top = await repo.list_top(limit=1)
    assert len(top) == 1
    assert top[0].telegram_id == 1


@pytest.mark.asyncio
async def test_user_repo_get_or_create_idempotent(async_db_session) -> None:
    repo = SQLAlchemyUserRepository(async_db_session)
    a = await repo.get_or_create_by_telegram_id(99, "x")
    b = await repo.get_or_create_by_telegram_id(99, "x")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_user_repo_update_missing_raises(async_db_session) -> None:
    repo = SQLAlchemyUserRepository(async_db_session)
    from src.entities.user import User

    ghost = User(
        id=99999,
        telegram_id=1,
        username=None,
        score=0,
        created_at=datetime.now(tz=UTC),
    )
    with pytest.raises(ValueError, match="not found"):
        await repo.update(ghost)


@pytest.mark.asyncio
async def test_quiz_question_create_and_get(async_db_session) -> None:
    repo = SQLAlchemyQuizQuestionRepository(async_db_session)
    data = QuizQuestionData(
        question_text="Q?",
        options=_opts(),
        correct_index=2,
        grade="easy",
    )
    qid = await repo.create(data)
    loaded = await repo.get_by_id(qid)
    assert loaded is not None
    assert loaded.question_text == "Q?"
    assert loaded.correct_index == 2
    assert await repo.get_by_id(99999) is None


@pytest.mark.asyncio
async def test_quiz_attempt_create_and_count(async_db_session) -> None:
    urepo = SQLAlchemyUserRepository(async_db_session)
    qrepo = SQLAlchemyQuizQuestionRepository(async_db_session)
    arepo = SQLAlchemyQuizAttemptRepository(async_db_session)
    user = await urepo.create(1, None)
    qid = await qrepo.create(
        QuizQuestionData("x", _opts(), 0, "easy"),
    )
    aid = await arepo.create(
        user_id=user.id,
        question_id=qid,
        chosen_index=0,
        is_correct=True,
        score=1,
        feedback="ok",
    )
    assert aid > 0
    assert await arepo.count_attempts(user_id=user.id, question_id=qid) == 1
    assert await arepo.count_attempts(user_id=user.id, question_id=999) == 0


@pytest.mark.asyncio
async def test_task_repo_get_by_id_and_daily_and_list(async_db_session) -> None:
    day = date(2026, 3, 1)
    async_db_session.add(
        TaskModel(
            title="T",
            description="D",
            difficulty="easy",
            daily_for=day,
            created_at=datetime.now(tz=UTC),
        ),
    )
    await async_db_session.flush()
    repo = SQLAlchemyTaskRepository(async_db_session)
    t = await repo.get_daily_task(day)
    assert t is not None
    assert t.title == "T"
    assert await repo.get_by_id(t.id) == t
    assert await repo.get_daily_task(date(2020, 1, 1)) is None
    published = await repo.list_published(limit=5)
    assert len(published) == 1


@pytest.mark.asyncio
async def test_submission_repo_create_get_list(async_db_session) -> None:
    urepo = SQLAlchemyUserRepository(async_db_session)
    user = await urepo.create(5, None)
    async_db_session.add(
        TaskModel(
            title="T",
            description="Desc",
            difficulty="medium",
            daily_for=None,
            created_at=datetime.now(tz=UTC),
        ),
    )
    await async_db_session.flush()
    task_row = (await async_db_session.execute(select(TaskModel.id).limit(1))).scalar_one()
    repo = SQLAlchemySubmissionRepository(async_db_session)
    draft = Submission(
        id=None,
        user_id=user.id,
        task_id=int(task_row),
        code="print(1)",
        feedback=None,
        score=0,
        created_at=datetime.now(tz=UTC),
    )
    saved = await repo.create(draft)
    assert saved.id is not None
    got = await repo.get_by_id(saved.id)
    assert got is not None
    assert got.code == "print(1)"
    lst = await repo.list_by_user(user.id, limit=10)
    assert len(lst) == 1
    assert await repo.get_by_id(99999) is None
