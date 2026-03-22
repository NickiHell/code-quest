"""SQLAlchemy implementation of AbstractSubmissionRepository."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.repositories import AbstractSubmissionRepository
from src.entities.submission import Submission
from src.infrastructure.db.models.submission import SubmissionModel


class SQLAlchemySubmissionRepository(AbstractSubmissionRepository):
    """Submission persistence via async SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, submission: Submission) -> Submission:
        """Persist a new submission."""
        model = SubmissionModel(
            user_id=submission.user_id,
            task_id=submission.task_id,
            code=submission.code,
            feedback=submission.feedback,
            score=submission.score,
            created_at=submission.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def get_by_id(self, submission_id: int) -> Submission | None:
        """Return submission by id."""
        row = await self._session.get(SubmissionModel, submission_id)
        return None if row is None else row.to_entity()

    async def list_by_user(self, user_id: int, limit: int = 10) -> list[Submission]:
        """Recent submissions for a user."""
        stmt = (
            select(SubmissionModel)
            .where(SubmissionModel.user_id == user_id)
            .order_by(desc(SubmissionModel.created_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [row.to_entity() for row in rows]
