from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram.exceptions import TelegramAPIError
from loguru import logger

T = TypeVar("T")

_INITIAL_BACKOFF_SEC = 5
_MAX_BACKOFF_SEC = 300


async def _wait_for_telegram[T](
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
