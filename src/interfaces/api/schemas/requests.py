"""Inbound request DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSubmissionRequest(BaseModel):
    """Payload for creating a submission."""

    telegram_id: int = Field(..., ge=1)
    username: str | None = Field(default=None, max_length=255)
    task_id: int = Field(..., ge=1)
    code: str = Field(..., min_length=1)
