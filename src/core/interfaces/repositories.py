from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.entities.submission import Submission
from src.entities.task import Task
from src.entities.user import User


class AbstractUserRepository(ABC):
    """Persistence port for users."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key."""

    @abstractmethod
    async def get_by_ids(self, user_ids: list[int]) -> dict[int, User]:
        """Загрузить пользователей по списку id; вернуть словарь id -> User."""

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Return a user by Telegram id."""

    @abstractmethod
    async def create(self, telegram_id: int, username: str | None) -> User:
        """Persist a new user."""

    @abstractmethod
    async def get_or_create_by_telegram_id(
        self,
        telegram_id: int,
        username: str | None,
    ) -> User:
        """Вернуть пользователя; при отсутствии — создать. Без гонки при параллельных запросах."""

    @abstractmethod
    async def update(self, user: User) -> User:
        """Persist changes to an existing user."""

    @abstractmethod
    async def list_top(self, limit: int = 10) -> list[User]:
        """Return users ordered by score (descending)."""


class AbstractTaskRepository(ABC):
    """Persistence port for tasks."""

    @abstractmethod
    async def get_by_id(self, task_id: int) -> Task | None:
        """Return a task by id."""

    @abstractmethod
    async def get_daily_task(self, day: date) -> Task | None:
        """Return the task scheduled for the given calendar day."""

    @abstractmethod
    async def list_published(self, limit: int = 50, offset: int = 0) -> list[Task]:
        """List published tasks for browsing."""


class AbstractSubmissionRepository(ABC):
    """Persistence port for code submissions."""

    @abstractmethod
    async def create(self, submission: Submission) -> Submission:
        """Persist a new submission."""

    @abstractmethod
    async def get_by_id(self, submission_id: int) -> Submission | None:
        """Return submission by id."""

    @abstractmethod
    async def list_by_user(self, user_id: int, limit: int = 10) -> list[Submission]:
        """Recent submissions for a user."""
