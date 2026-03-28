from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Chat, Message

from src.interfaces.bot.handlers import errors as errors_handler
from src.interfaces.bot.handlers import menu as menu_handler
from src.interfaces.bot.handlers import start as start_handler
from src.interfaces.bot.handlers import task as task_handler


def _msg_private(text: str | None = None) -> Message:
    chat = MagicMock(spec=Chat)
    chat.type = "private"
    m = MagicMock(spec=Message)
    m.chat = chat
    m.text = text
    m.answer = AsyncMock()
    m.reply = AsyncMock()
    return m


def _msg_group() -> Message:
    chat = MagicMock(spec=Chat)
    chat.type = "group"
    m = MagicMock(spec=Message)
    m.chat = chat
    m.reply = AsyncMock()
    return m


@pytest.mark.asyncio
async def test_start_private_sends_welcome() -> None:
    m = _msg_private()
    fake_settings = MagicMock()
    with (
        patch("src.interfaces.bot.handlers.start.Settings", return_value=fake_settings),
        patch(
            "src.interfaces.bot.handlers.start.main_menu_keyboard",
            return_value=MagicMock(),
        ),
    ):
        await start_handler.handle_start_private(m)
    m.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_group_replies_with_inline() -> None:
    m = _msg_group()
    bot = AsyncMock()
    bot.me = AsyncMock(return_value=MagicMock(username="codequest_bot"))
    fake_settings = MagicMock()
    with (
        patch("src.interfaces.bot.handlers.start.Settings", return_value=fake_settings),
        patch(
            "src.interfaces.bot.handlers.start.group_menu_inline",
            return_value=MagicMock(),
        ),
    ):
        await start_handler.handle_start_group(m, bot)
    m.reply.assert_awaited_once()


@pytest.mark.asyncio
async def test_cmd_app_private_branch() -> None:
    m = _msg_private()
    bot = AsyncMock()
    bot.me = AsyncMock(return_value=MagicMock(username="b"))
    fake_settings = MagicMock()
    with (
        patch("src.interfaces.bot.handlers.menu.Settings", return_value=fake_settings),
        patch(
            "src.interfaces.bot.handlers.menu.private_menu_inline",
            return_value=MagicMock(),
        ),
        patch(
            "src.interfaces.bot.handlers.menu.main_menu_keyboard",
            return_value=MagicMock(),
        ),
    ):
        await menu_handler.cmd_app(m, bot)
    assert m.answer.await_count == 2


@pytest.mark.asyncio
async def test_cmd_app_group_branch() -> None:
    chat = MagicMock(spec=Chat)
    chat.type = "supergroup"
    m = MagicMock(spec=Message)
    m.chat = chat
    m.reply = AsyncMock()
    bot = AsyncMock()
    bot.me = AsyncMock(return_value=MagicMock(username="b"))
    fake_settings = MagicMock()
    with (
        patch("src.interfaces.bot.handlers.menu.Settings", return_value=fake_settings),
        patch(
            "src.interfaces.bot.handlers.menu.group_menu_inline",
            return_value=MagicMock(),
        ),
    ):
        await menu_handler.cmd_app(m, bot)
    m.reply.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_private_hint() -> None:
    m = _msg_private("hello")
    await task_handler.fallback_private_hint(m)
    m.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_log_dispatcher_error_no_update() -> None:
    event = MagicMock()
    event.update = None
    event.exception = ValueError("x")
    bot = AsyncMock()
    with patch("src.interfaces.bot.handlers.errors.logger"):
        out = await errors_handler.log_dispatcher_error(event, bot)
    assert out is True


@pytest.mark.asyncio
async def test_log_dispatcher_error_notifies_user() -> None:
    from aiogram.types import Update

    event = MagicMock()
    event.update = MagicMock(spec=Update)
    event.update.update_id = 1
    event.exception = ValueError("x")
    bot = AsyncMock()
    with (
        patch("src.interfaces.bot.handlers.errors.logger"),
        patch(
            "src.interfaces.bot.handlers.errors.should_notify_user",
            return_value=True,
        ),
        patch(
            "src.interfaces.bot.handlers.errors.brief_user_message",
            return_value="msg",
        ),
        patch(
            "src.interfaces.bot.handlers.errors.notify_user_about_error",
            new=AsyncMock(),
        ) as notify,
    ):
        out = await errors_handler.log_dispatcher_error(event, bot)
    assert out is True
    notify.assert_awaited_once()
