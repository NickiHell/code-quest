"""SQLAlchemy implementation of AbstractUserRepository."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.interfaces.repositories import AbstractUserRepository
from src.entities.user import User
from src.infrastructure.db.models.user import UserModel


class SQLAlchemyUserRepository(AbstractUserRepository):
    """User persistence via async SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key."""
        row = await self._session.get(UserModel, user_id)
        return None if row is None else row.to_entity()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Return a user by Telegram id."""
        stmt = select(UserModel).where(UserModel.telegram_id == telegram_id).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return None if row is None else row.to_entity()

    async def create(self, telegram_id: int, username: str | None) -> User:
        """Persist a new user."""
        from datetime import UTC, datetime

        model = UserModel(
            telegram_id=telegram_id,
            username=username,
            score=0,
            created_at=datetime.now(tz=UTC),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def update(self, user: User) -> User:
        """Persist changes to an existing user."""
        model = await self._session.get(UserModel, user.id)
        if model is None:
            msg = f"User id={user.id} not found"
            raise ValueError(msg)
        model.score = user.score
        model.username = user.username
        await self._session.flush()
        return model.to_entity()

    async def list_top(self, limit: int = 10) -> list[User]:
        """Return users ordered by score (descending)."""
        stmt = select(UserModel).order_by(desc(UserModel.score)).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [row.to_entity() for row in rows]
