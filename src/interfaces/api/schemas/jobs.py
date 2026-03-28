from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class JobAcceptedResponse(BaseModel):
    job_id: str
    status_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    result: dict[str, object] | None = None
    error: str | None = None
