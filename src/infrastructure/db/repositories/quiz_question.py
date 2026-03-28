from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.quiz_repositories import AbstractQuizQuestionRepository
from src.entities.quiz import QuizQuestionData
from src.infrastructure.db.models.quiz_question import QuizQuestionModel


class SQLAlchemyQuizQuestionRepository(AbstractQuizQuestionRepository):
    """Реализация хранения вопросов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: QuizQuestionData) -> int:
        """Сохранить вопрос, вернуть id."""
        model = QuizQuestionModel(
            question_text=data.question_text,
            options=list(data.options),
            correct_index=data.correct_index,
            grade=data.grade,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return int(model.id)

    async def get_by_id(self, question_id: int) -> QuizQuestionData | None:
        """Загрузить вопрос по id."""
        row = await self._session.get(QuizQuestionModel, question_id)
        return None if row is None else row.to_domain()
