from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.interfaces.repositories import AbstractUserRepository
from src.interfaces.api.deps import get_user_repository
from src.interfaces.api.schemas.responses import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    telegram_id: int = Query(..., ge=1),
    repo: AbstractUserRepository = Depends(get_user_repository),
) -> UserResponse:
    """Lookup a user by Telegram id (Mini App bootstrap)."""
    user = await repo.get_by_telegram_id(telegram_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        score=user.score,
        created_at=user.created_at,
    )
