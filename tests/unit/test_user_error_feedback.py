from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)

from src.interfaces.bot import user_error_feedback as uef

_m = MagicMock()


def test_should_notify_user_filters_harmless_bad_request() -> None:
    assert uef.should_notify_user(TelegramBadRequest(_m, "message is not modified")) is False
    assert uef.should_notify_user(TelegramBadRequest(_m, "query is too old")) is False
    assert uef.should_notify_user(TelegramBadRequest(_m, "query id is invalid")) is False
    assert uef.should_notify_user(TelegramBadRequest(_m, "message to edit not found")) is False
    assert uef.should_notify_user(TelegramBadRequest(_m, "other")) is True


def test_brief_user_message_covers_types() -> None:
    assert "интернет" in uef.brief_user_message(TelegramNetworkError(_m, "x"))
    assert "Подождите" in uef.brief_user_message(TelegramRetryAfter(_m, "m", retry_after=1))
    assert "бан" in uef.brief_user_message(TelegramForbiddenError(_m, "x"))
    assert "недоступны" in uef.brief_user_message(TelegramNotFound(_m, "x"))
    assert "авторизации" in uef.brief_user_message(TelegramUnauthorizedError(_m, "x"))
    assert "Telegram" in uef.brief_user_message(TelegramServerError(_m, "x"))
    assert "/app" in uef.brief_user_message(TelegramBadRequest(_m, "x"))
    assert "Таймаут" in uef.brief_user_message(TimeoutError())
    assert "Таймаут" in uef.brief_user_message(ConnectionError())
    assert "Некорректные" in uef.brief_user_message(ValueError("x"))
    assert "/app" in uef.brief_user_message(RuntimeError("x"))


@pytest.mark.asyncio
async def test_try_answer_via_standard_message() -> None:
    msg = AsyncMock()
    upd = MagicMock()
    upd.message = msg
    assert await uef._try_answer_via_standard_message(upd, "hi") is True
    msg.answer.assert_awaited_once_with("hi")


@pytest.mark.asyncio
async def test_try_answer_standard_message_missing_returns_false() -> None:
    upd = SimpleNamespace()
    for field in uef._STD_MESSAGE_FIELDS:
        setattr(upd, field, None)
    assert await uef._try_answer_via_standard_message(upd, "t") is False


@pytest.mark.asyncio
async def test_try_answer_callback_when_no_callback() -> None:
    upd = SimpleNamespace(callback_query=None)
    assert await uef._try_answer_via_callback(upd, "t") is False


@pytest.mark.asyncio
async def test_notify_user_channel_post_only_returns_quietly() -> None:
    from aiogram.types import Update

    upd = MagicMock(spec=Update)
    upd.message = None
    upd.callback_query = None
    upd.channel_post = MagicMock()
    with patch.object(uef.logger, "debug"):
        await uef.notify_user_about_error(AsyncMock(), upd, "e")


@pytest.mark.asyncio
async def test_notify_user_about_error_swallows_send_errors() -> None:
    upd = MagicMock()
    upd.message = AsyncMock()
    upd.message.answer = AsyncMock(side_effect=RuntimeError("fail"))
    with patch("src.interfaces.bot.user_error_feedback.logger"):
        await uef.notify_user_about_error(AsyncMock(), upd, "e")


@pytest.mark.asyncio
async def test_try_answer_via_callback_alert_fallback() -> None:
    cq = AsyncMock()
    cq.answer = AsyncMock(side_effect=TelegramBadRequest(_m, "x"))
    cq.message = AsyncMock()
    upd = MagicMock()
    upd.callback_query = cq
    assert await uef._try_answer_via_callback(upd, "long " * 50) is True
    cq.message.answer.assert_awaited()
