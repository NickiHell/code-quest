from __future__ import annotations

import asyncio
from typing import Final

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from aiogram.types import Update
from loguru import logger

_MAX_CALLBACK_ALERT: Final[int] = 200
_STD_MESSAGE_FIELDS: Final[tuple[str, ...]] = (
    "message",
    "edited_message",
    "business_message",
    "edited_business_message",
)


def should_notify_user(exc: BaseException) -> bool:
    """Не беспокоить пользователя на безвредных/ожидаемых ошибках API."""
    if isinstance(exc, TelegramBadRequest):
        low = str(exc).lower()
        if "message is not modified" in low:
            return False
        if "query is too old" in low or "query id is invalid" in low:
            return False
        if "message to edit not found" in low:
            return False
    return True


def brief_user_message(exc: BaseException) -> str:
    """Короткое объяснение причины для человека (без стеков и внутренних полей)."""
    if isinstance(exc, TelegramNetworkError):
        msg = "Не удалось связаться с Telegram. Проверьте интернет и попробуйте снова."
    elif isinstance(exc, TelegramRetryAfter):
        msg = "Слишком много действий подряд. Подождите немного и повторите."
    elif isinstance(exc, TelegramForbiddenError):
        msg = "Бот не может написать в этот чат: возможен бан или не хватает прав."
    elif isinstance(exc, TelegramNotFound):
        msg = "Чат или сообщение недоступны. Обновите диалог или откройте бота заново."
    elif isinstance(exc, TelegramUnauthorizedError):
        msg = "Ошибка авторизации бота. Обратитесь к администратору сервиса."
    elif isinstance(exc, TelegramServerError):
        msg = "Временная ошибка на стороне Telegram. Попробуйте через минуту."
    elif isinstance(exc, TelegramBadRequest):
        msg = "Запрос не выполнен. Попробуйте ещё раз или команду /app."
    elif isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        msg = "Таймаут или обрыв сети. Попробуйте позже."
    elif isinstance(exc, ValueError):
        msg = "Некорректные данные. Попробуйте ещё раз или /app."
    else:
        msg = "Что-то пошло не так. Попробуйте команду /app чуть позже."
    return msg


async def _try_answer_via_standard_message(update: Update, text: str) -> bool:
    for field in _STD_MESSAGE_FIELDS:
        m = getattr(update, field, None)
        if m is not None:
            await m.answer(text)
            return True
    return False


async def _try_answer_via_callback(update: Update, text: str) -> bool:
    cq = update.callback_query
    if cq is None:
        return False
    alert = text[:_MAX_CALLBACK_ALERT]
    try:
        await cq.answer(text=alert, show_alert=True)
    except TelegramBadRequest:
        if cq.message is not None:
            await cq.message.answer(text)
    return True


async def notify_user_about_error(_bot: Bot, update: Update, text: str) -> None:
    """Отправить пользователю короткое сообщение, если из апдейта это возможно."""
    try:
        if await _try_answer_via_standard_message(update, text):
            return
        if await _try_answer_via_callback(update, text):
            return
        if update.channel_post is not None or update.edited_channel_post is not None:
            return
    except Exception as send_exc:  # noqa: BLE001
        logger.debug("не удалось отправить пользователю текст об ошибке: {}", send_exc)
