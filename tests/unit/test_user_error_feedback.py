"""Тексты для пользователя при ошибках бота."""

from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

from src.interfaces.bot.user_error_feedback import brief_user_message, should_notify_user


def test_brief_network() -> None:
    msg = brief_user_message(TelegramNetworkError(method=None, message="x"))  # type: ignore[arg-type]
    assert "Telegram" in msg or "связ" in msg.lower()


def test_brief_generic() -> None:
    msg = brief_user_message(RuntimeError("secret internal"))
    assert "secret" not in msg
    assert "/menu" in msg


def test_skip_not_modified() -> None:
    exc = TelegramBadRequest(method=None, message="message is not modified")  # type: ignore[arg-type]
    assert should_notify_user(exc) is False


def test_timeout_maps() -> None:
    text = brief_user_message(TimeoutError()).lower()
    assert "таймаут" in text or "сеть" in text
