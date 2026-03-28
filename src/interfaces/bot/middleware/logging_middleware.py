from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger


class TelegramEventLoggingMiddleware(BaseMiddleware):
    """Пишет в лог каждое сообщение и callback (чат, пользователь, текст)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            text = event.text or event.caption or ""
            logger.info(
                "telegram message: chat_type={} chat_id={} user_id={} text={!r}",
                event.chat.type if event.chat else None,
                event.chat.id if event.chat else None,
                event.from_user.id if event.from_user else None,
                text[:2000],
            )
        elif isinstance(event, CallbackQuery):
            logger.info(
                "telegram callback: chat_id={} user_id={} data={!r}",
                event.message.chat.id if event.message and event.message.chat else None,
                event.from_user.id if event.from_user else None,
                (event.data or "")[:500],
            )
        return await handler(event, data)
