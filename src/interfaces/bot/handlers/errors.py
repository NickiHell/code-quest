from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types.error_event import ErrorEvent
from loguru import logger

from src.interfaces.bot.user_error_feedback import (
    brief_user_message,
    notify_user_about_error,
    should_notify_user,
)

router = Router(name="errors")


@router.errors()
async def log_dispatcher_error(event: ErrorEvent, bot: Bot) -> bool:
    """Логируем исключение; пользователю — коротко и без внутренностей."""
    uid = event.update.update_id if event.update else None
    logger.opt(exception=event.exception).error("ошибка обработки Telegram update_id={}", uid)

    if event.update is None or not should_notify_user(event.exception):
        return True

    text = brief_user_message(event.exception)
    await notify_user_about_error(bot, event.update, text)
    return True
