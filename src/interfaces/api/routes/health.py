"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

from src.interfaces.api.schemas.responses import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe for orchestrators and load balancers."""
    return HealthResponse(status="ok", version="0.1.0")
