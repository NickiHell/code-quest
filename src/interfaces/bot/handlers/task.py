from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message


async def fallback_private_hint(message: Message) -> None:
    """Подсказка только в личных сообщениях."""
    await message.answer("Команда /app — кнопки Mini App, или откройте приложение кнопкой снизу.")


def mount_task_handlers(root: Router) -> None:
    r = Router(name="task")
    r.message.register(
        fallback_private_hint,
        F.chat.type == "private",
        F.text,
        ~F.text.startswith("/"),
    )
    root.include_router(r)
