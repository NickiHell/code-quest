from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.entities.submission import Submission


@pytest.fixture
def base_submission() -> Submission:
    return Submission(
        id=1,
        user_id=2,
        task_id=3,
        code="print('x')",
        feedback=None,
        score=0,
        created_at=datetime.now(tz=UTC),
    )


@pytest.mark.parametrize(
    ("feedback", "score"),
    [
        ("nice", 8),
        ("", 0),
        ("detailed review", 100),
    ],
)
def test_with_result_copies_identity_and_updates_score(
    base_submission: Submission,
    feedback: str,
    score: int,
) -> None:
    out = base_submission.with_result(feedback, score)
    assert out.feedback == feedback
    assert out.score == score
    assert out.id == base_submission.id
    assert out.user_id == base_submission.user_id
    assert out.task_id == base_submission.task_id
    assert out.code == base_submission.code
    assert out.created_at == base_submission.created_at
