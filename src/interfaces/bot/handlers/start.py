"""Команда /start — отдельно для лички и для групп."""

from __future__ import annotations

from aiogram import Bot, F, Router
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
        "Добро пожаловать в <b>Code Quest</b> — квиз по коду, шахматам, го и не только.\n\n"
        "Нажмите кнопку <b>Mini App: Code Quest</b> внизу — приложение откроется "
        "<b>внутри Telegram</b>.\n"
        "Тему, сложность и лидерборд смотрите в приложении. Команда /app — кнопки Mini App.",
        reply_markup=main_menu_keyboard(settings),
    )


@router.message(CommandStart(), F.chat.type.in_({"group", "supergroup"}))
async def handle_start_group(message: Message, bot: Bot) -> None:
    """Кратко в группе + inline (Mini App)."""
    settings = Settings()
    me = await bot.me()
    await message.reply(
        "Code Quest в этой группе.\n"
        "Используйте /app — кнопка <b>Mini App</b> открывает квиз "
        "<b>внутри Telegram</b> (t.me).",
        reply_markup=group_menu_inline(settings, bot_username=me.username),
    )
