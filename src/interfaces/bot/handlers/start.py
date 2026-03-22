"""Команда /start — отдельно для лички и для групп."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.core.config import Settings
from src.interfaces.bot.keyboards.inline import group_menu_inline
from src.interfaces.bot.keyboards.main import main_menu_keyboard

router = Router(name="start")


@router.message(CommandStart(), F.chat.type == "private")
async def handle_start_private(message: Message) -> None:
    """Приветствие в личке: reply-клавиатура с Web App."""
    settings = Settings()
    await message.answer(
        "Добро пожаловать в <b>Code Quest</b> — ежедневные задачи по программированию.\n\n"
        "Нажмите <b>«Открыть Code Quest»</b> внизу — приложение откроется <b>внутри Telegram</b>.\n"
        "Статистика и админка — в <b>веб-панели</b> (команда /menu).",
        reply_markup=main_menu_keyboard(settings),
    )


@router.message(CommandStart(), F.chat.type.in_({"group", "supergroup"}))
async def handle_start_group(message: Message) -> None:
    """Кратко в группе + inline (Mini App и веб)."""
    settings = Settings()
    await message.reply(
        "Code Quest в этой группе.\n"
        "Используйте /menu — там кнопка <b>Mini App</b> (внутри Telegram) "
        "и ссылка на <b>веб-панель</b>.",
        reply_markup=group_menu_inline(settings),
    )
