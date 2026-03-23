"""Единственная слэш-команда для Mini App: /app."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from src.core.config import Settings
from src.interfaces.bot.keyboards.inline import group_menu_inline, private_menu_inline
from src.interfaces.bot.keyboards.main import main_menu_keyboard

router = Router(name="menu")


def _is_group(message: Message) -> bool:
    return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


@router.message(Command("app"))
async def cmd_app(message: Message, bot: Bot) -> None:
    """Кнопки Mini App."""
    settings = Settings()
    me = await bot.me()
    if _is_group(message):
        text = (
            "<b>Code Quest</b>\n\n"
            "Нажмите кнопку «Code Quest — Mini App» — приложение откроется "
            "<b>внутри Telegram</b> (ссылка t.me). "
            "В квизе выберите тему и грейд (junior / middle / senior), "
            "5 вариантов ответа; очки зависят от сложности."
        )
        await message.reply(
            text,
            reply_markup=group_menu_inline(settings, bot_username=me.username),
        )
    else:
        text = (
            "<b>Code Quest</b>\n\n"
            "Квиз: Python, JS, алгоритмы, шахматы, го и др.; "
            "5 вариантов ответа; очки зависят от грейда.\n\n"
            "Нажмите кнопку «Mini App» ниже или на клавиатуре — "
            "приложение откроется внутри Telegram."
        )
        await message.answer(
            text,
            reply_markup=private_menu_inline(settings),
        )
        await message.answer(
            "Или пользуйтесь клавиатурой внизу:",
            reply_markup=main_menu_keyboard(settings),
        )
