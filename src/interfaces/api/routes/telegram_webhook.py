from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)


@router.post("/webhook/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    if secret != settings.telegram_webhook_secret:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not found")

    bot: Bot = request.app.state.telegram_bot
    dp = request.app.state.telegram_dp

    try:
        payload = await request.json()
        update = Update.model_validate(payload)
    except Exception as exc:
        logger.warning("invalid telegram webhook json: %s", exc)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="invalid update",
        ) from exc

    await dp.feed_update(bot, update)
    return {}
