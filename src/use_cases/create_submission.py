from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.core.exceptions import DomainValidationError, NotFoundError
from src.core.interfaces.ai_provider import AbstractAIProvider
from src.core.interfaces.leaderboard import AbstractLeaderboard
from src.core.interfaces.repositories import (
    AbstractSubmissionRepository,
    AbstractTaskRepository,
    AbstractUserRepository,
)
from src.entities.submission import Submission

logger = logging.getLogger(__name__)


def _score_from_feedback(feedback: str) -> int:
    """Heuristic placeholder until structured model output is available."""
    lowered = feedback.lower()
    if "incorrect" in lowered or "wrong" in lowered:
        return 0
    if "excellent" in lowered or "perfect" in lowered:
        return 10
    return 5


class CreateSubmissionUseCase:
    """Orchestrates validation, AI review, persistence, and leaderboard updates."""

    def __init__(
        self,
        *,
        tasks: AbstractTaskRepository,
        users: AbstractUserRepository,
        submissions: AbstractSubmissionRepository,
        ai: AbstractAIProvider,
        leaderboard: AbstractLeaderboard,
    ) -> None:
        self._tasks = tasks
        self._users = users
        self._submissions = submissions
        self._ai = ai
        self._leaderboard = leaderboard

    async def execute(
        self,
        *,
        telegram_id: int,
        username: str | None,
        task_id: int,
        code: str,
    ) -> Submission:
        """Persist submission after AI feedback and score update."""
        if not code.strip():
            raise DomainValidationError("Code must not be empty")

        task = await self._tasks.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Task not found")

        user = await self._users.get_or_create_by_telegram_id(telegram_id, username)

        feedback = await self._ai.evaluate_code(code, task.description)
        points = _score_from_feedback(feedback)

        draft = Submission(
            id=None,
            user_id=user.id,
            task_id=task.id,
            code=code,
            feedback=feedback,
            score=points,
            created_at=datetime.now(tz=UTC),
        )
        saved = await self._submissions.create(draft)

        scored_user = user.add_score(points)
        await self._users.update(scored_user)
        await self._leaderboard.add_score(user_id=user.id, points=points)

        logger.info("Submission %s scored with %s points", saved.id, points)
        return saved
