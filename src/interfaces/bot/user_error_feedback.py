"""Краткие ответы пользователю при сбоях без утечки внутренних деталей."""

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

# Лимит Telegram для callback answer + show_alert
_MAX_CALLBACK_ALERT: Final[int] = 200


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
        return "Не удалось связаться с Telegram. Проверьте интернет и попробуйте снова."
    if isinstance(exc, TelegramRetryAfter):
        return "Слишком много действий подряд. Подождите немного и повторите."
    if isinstance(exc, TelegramForbiddenError):
        return "Бот не может написать в этот чат: возможен бан или не хватает прав."
    if isinstance(exc, TelegramNotFound):
        return "Чат или сообщение недоступны. Обновите диалог или откройте бота заново."
    if isinstance(exc, TelegramUnauthorizedError):
        return "Ошибка авторизации бота. Обратитесь к администратору сервиса."
    if isinstance(exc, TelegramServerError):
        return "Временная ошибка на стороне Telegram. Попробуйте через минуту."
    if isinstance(exc, TelegramBadRequest):
        return "Запрос не выполнен. Попробуйте ещё раз или команду /menu."
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        return "Таймаут или обрыв сети. Попробуйте позже."
    if isinstance(exc, ValueError):
        return "Некорректные данные. Попробуйте ещё раз или /menu."
    return "Что-то пошло не так. Попробуйте команду /menu чуть позже."


async def notify_user_about_error(bot: Bot, update: Update, text: str) -> None:
    """Отправить пользователю короткое сообщение, если из апдейта это возможно."""
    try:
        if update.message:
            await update.message.answer(text)
            return
        if update.edited_message:
            await update.edited_message.answer(text)
            return
        if update.business_message:
            await update.business_message.answer(text)
            return
        if update.edited_business_message:
            await update.edited_business_message.answer(text)
            return
        if update.callback_query:
            cq = update.callback_query
            alert = text[:_MAX_CALLBACK_ALERT]
            try:
                await cq.answer(text=alert, show_alert=True)
            except TelegramBadRequest:
                if cq.message:
                    await cq.message.answer(text)
            return
        if update.channel_post:
            return
        if update.edited_channel_post:
            return
    except Exception as send_exc:
        logger.debug("не удалось отправить пользователю текст об ошибке: {}", send_exc)
