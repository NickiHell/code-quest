from __future__ import annotations

from aiogram import Dispatcher

from src.interfaces.bot.handlers import errors as error_handlers
from src.interfaces.bot.handlers import menu as menu_handlers
from src.interfaces.bot.handlers import start as start_handlers
from src.interfaces.bot.handlers import task as task_handlers
from src.interfaces.bot.middleware.logging_middleware import TelegramEventLoggingMiddleware


def build_dispatcher() -> Dispatcher:
    """Новый Dispatcher с отдельными Router-экземплярами (тесты создают несколько приложений)."""
    dp = Dispatcher()
    dp.message.middleware(TelegramEventLoggingMiddleware())
    dp.callback_query.middleware(TelegramEventLoggingMiddleware())
    error_handlers.mount_error_handlers(dp)
    start_handlers.mount_start_handlers(dp)
    menu_handlers.mount_menu_handlers(dp)
    task_handlers.mount_task_handlers(dp)
    return dp
