"""Фолбэк в личке; в группах молчим, чтобы не спамить."""

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
    await message.answer("Команды: /menu, /app, /help — или откройте Mini App кнопкой снизу.")
