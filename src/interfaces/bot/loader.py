from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from loguru import logger

from src.core.config import Settings
from src.infrastructure.logging_config import configure_loguru
from src.interfaces.bot.handlers import errors as error_handlers
from src.interfaces.bot.handlers import menu as menu_handlers
from src.interfaces.bot.handlers import start as start_handlers
from src.interfaces.bot.handlers import task as task_handlers
from src.interfaces.bot.middleware.logging_middleware import TelegramEventLoggingMiddleware
from src.interfaces.bot.setup import setup_bot_profile

T = TypeVar("T")

_INITIAL_BACKOFF_SEC = 5
_MAX_BACKOFF_SEC = 300


async def _wait_for_telegram(
    label: str,
    call: Callable[[], Awaitable[T]],
) -> T:
    """Повторять вызов при TelegramAPIError с экспоненциальной паузой (без выхода из процесса)."""
    delay = _INITIAL_BACKOFF_SEC
    while True:
        try:
            return await call()
        except TelegramAPIError as exc:
            logger.warning(
                "{}: {} — повтор через {} с (проверьте сеть/VPN/DNS до api.telegram.org)",
                label,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, _MAX_BACKOFF_SEC)


async def _run_polling_loop(bot: Bot, dp: Dispatcher, settings: Settings) -> None:
    """Подключение к Telegram и long polling; при сбое можно вызвать снова."""
    me = await _wait_for_telegram("getMe", bot.get_me)
    logger.info("связь с Telegram OK: @{} (id={})", me.username, me.id)

    await setup_bot_profile(bot, settings)

    await _wait_for_telegram(
        "delete_webhook",
        lambda: bot.delete_webhook(drop_pending_updates=True),
    )
    logger.info("webhook сброшен, long polling — жду апдейты")

    await dp.start_polling(bot)


async def main() -> None:
    """Логирование, роутеры, бесконечный цикл с переподключением при сетевых сбоях."""
    settings = Settings()
    configure_loguru(
        level=settings.log_level,
        app_env=settings.app_env,
        log_dir=settings.log_dir,
    )

    logger.info("Mini App (WebView в Telegram): {}", settings.webapp_url)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(TelegramEventLoggingMiddleware())
    dp.callback_query.middleware(TelegramEventLoggingMiddleware())
    dp.include_router(error_handlers.router)
    dp.include_router(start_handlers.router)
    dp.include_router(menu_handlers.router)
    dp.include_router(task_handlers.router)

    outer_delay = _INITIAL_BACKOFF_SEC
    while True:
        try:
            await _run_polling_loop(bot, dp, settings)
            logger.warning(
                "start_polling завершился без исключения — пауза {} с перед новым циклом",
                outer_delay,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "цикл polling прерван ({}), пауза {} с перед перезапуском",
                exc,
                outer_delay,
            )
        await asyncio.sleep(outer_delay)
        outer_delay = min(outer_delay * 2, _MAX_BACKOFF_SEC)


if __name__ == "__main__":
    asyncio.run(main())
