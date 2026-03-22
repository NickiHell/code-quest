"""User submission for a task."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Submission:
    """Source code sent for automated review."""

    id: int | None
    user_id: int
    task_id: int
    code: str
    feedback: str | None
    score: int
    created_at: datetime

    def with_result(self, feedback: str, score: int) -> Submission:
        """Return a copy with AI feedback and awarded points."""
        return Submission(
            id=self.id,
            user_id=self.user_id,
            task_id=self.task_id,
            code=self.code,
            feedback=feedback,
            score=score,
            created_at=self.created_at,
        )
