from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, User

from src.core.config import Settings
from src.interfaces.bot import loader as loader_mod
from src.interfaces.bot import setup as setup_mod
from src.interfaces.bot.middleware import logging_middleware as mw_mod
from src.interfaces.bot.middleware.logging_middleware import TelegramEventLoggingMiddleware

_m = MagicMock()


@pytest.mark.asyncio
async def test_telegram_logging_middleware_message() -> None:
    mw = TelegramEventLoggingMiddleware()
    chat = MagicMock()
    chat.type = "private"
    chat.id = 1
    user = MagicMock(spec=User)
    user.id = 2
    msg = MagicMock(spec=Message)
    msg.chat = chat
    msg.from_user = user
    msg.text = "hi"
    msg.caption = None
    handler = AsyncMock(return_value="done")
    with patch.object(mw_mod.logger, "info"):
        out = await mw(handler, msg, {})
    assert out == "done"
    handler.assert_awaited_once_with(msg, {})


@pytest.mark.asyncio
async def test_telegram_logging_middleware_callback() -> None:
    mw = TelegramEventLoggingMiddleware()
    cq = MagicMock(spec=CallbackQuery)
    cq.message = MagicMock()
    cq.message.chat = MagicMock()
    cq.message.chat.id = 3
    cq.from_user = MagicMock()
    cq.from_user.id = 4
    cq.data = "x"
    handler = AsyncMock(return_value=1)
    with patch.object(mw_mod.logger, "info"):
        await mw(handler, cq, {})
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_bot_profile_success() -> None:
    bot = AsyncMock()
    settings = Settings(
        secret_key="x" * 16,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        yandex_folder_id="f",
        yandex_auth="k",
    )
    await setup_mod.setup_bot_profile(bot, settings)
    assert bot.set_my_commands.await_count == 2
    bot.set_chat_menu_button.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_bot_profile_logs_on_api_errors() -> None:
    bot = AsyncMock()
    bot.set_my_commands = AsyncMock(side_effect=TelegramBadRequest(_m, "bad"))
    bot.set_chat_menu_button = AsyncMock(side_effect=TelegramBadRequest(_m, "bad"))
    settings = Settings(
        secret_key="x" * 16,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        yandex_folder_id="f",
        yandex_auth="k",
    )
    with patch.object(setup_mod.logger, "warning") as w:
        await setup_mod.setup_bot_profile(bot, settings)
    assert w.call_count >= 1


@pytest.mark.asyncio
async def test_wait_for_telegram_retries() -> None:
    ok = MagicMock()
    call = AsyncMock(side_effect=[TelegramBadRequest(_m, "fail"), ok])
    with patch("asyncio.sleep", new=AsyncMock()):
        out = await loader_mod._wait_for_telegram("t", call)
    assert out is ok
    assert call.await_count == 2
