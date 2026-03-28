from __future__ import annotations

from datetime import UTC, datetime

from src.entities.submission import Submission


def test_with_result_copies_and_updates_feedback() -> None:
    s = Submission(
        id=1,
        user_id=2,
        task_id=3,
        code="x",
        feedback=None,
        score=0,
        created_at=datetime.now(tz=UTC),
    )
    out = s.with_result("nice", 8)
    assert out.feedback == "nice"
    assert out.score == 8
    assert out.id == s.id
