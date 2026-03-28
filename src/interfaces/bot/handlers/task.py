from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

router = Router(name="task")


@router.message(
    F.chat.type == "private",
    F.text,
    ~F.text.startswith("/"),
)
async def fallback_private_hint(message: Message) -> None:
    """Подсказка только в личных сообщениях."""
    await message.answer("Команда /app — кнопки Mini App, или откройте приложение кнопкой снизу.")
