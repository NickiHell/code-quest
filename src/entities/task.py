"""Programming task definition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Task:
    """A published coding challenge."""

    id: int
    title: str
    description: str
    difficulty: str
    daily_for: date | None
    created_at: datetime
