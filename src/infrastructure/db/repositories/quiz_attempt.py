"""SQLAlchemy: quiz_attempts."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.quiz_repositories import AbstractQuizAttemptRepository
from src.infrastructure.db.models.quiz_attempt import QuizAttemptModel


class SQLAlchemyQuizAttemptRepository(AbstractQuizAttemptRepository):
    """Реализация хранения попыток."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: int,
        question_id: int,
        chosen_index: int,
        is_correct: bool,
        score: int,
        feedback: str,
    ) -> int:
        """Создать запись попытки, вернуть id."""
        model = QuizAttemptModel(
            user_id=user_id,
            question_id=question_id,
            chosen_index=chosen_index,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return int(model.id)
