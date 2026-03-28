from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSubmissionRequest(BaseModel):
    """Payload for creating a submission (user from X-Telegram-Init-Data)."""

    task_id: int = Field(..., ge=1)
    code: str = Field(..., min_length=1)
