from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeDefault,
    MenuButtonWebApp,
    WebAppInfo,
)
from loguru import logger

from src.core.config import Settings


async def setup_bot_profile(bot: Bot, settings: Settings) -> None:
    """Команды в сайдбаре Telegram + кнопка «меню» с Web App.

    Сетевые или прочие ошибки API логируются; процесс не падает — polling может работать.
    """
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="app", description="Открыть Code Quest (квиз)"),
            ],
            scope=BotCommandScopeDefault(),
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_commands (личные чаты) не применены: {} — команды в клиенте могут быть старыми",
            exc,
        )

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="app", description="Открыть Code Quest (квиз)"),
            ],
            scope=BotCommandScopeAllGroupChats(),
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_my_commands (группы) не применены: {} — в группах команды могут отличаться",
            exc,
        )

    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Code Quest",
                web_app=WebAppInfo(url=str(settings.webapp_url)),
            ),
        )
    except TelegramAPIError as exc:
        logger.warning(
            "set_chat_menu_button не применён: {} — кнопка меню в Telegram может быть без Mini App",
            exc,
        )
