"""Outbound response DTOs."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Service health payload."""

    status: str
    version: str


class SubmissionResponse(BaseModel):
    """Persisted submission."""

    id: int
    user_id: int
    task_id: int
    code: str
    feedback: str | None
    score: int
    created_at: datetime


class TaskResponse(BaseModel):
    """Task exposed to clients."""

    id: int
    title: str
    description: str
    difficulty: str
    daily_for: date | None
    created_at: datetime


class UserResponse(BaseModel):
    """User profile."""

    id: int
    telegram_id: int
    username: str | None
    score: int
    created_at: datetime
