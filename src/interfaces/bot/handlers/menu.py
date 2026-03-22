"""Команды /menu, /app, /help — в личке и в группах."""

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


@router.message(Command("menu"))
async def cmd_menu(message: Message, bot: Bot) -> None:
    """Показать кнопки Mini App и веб-панели."""
    settings = Settings()
    me = await bot.me()
    text = (
        "<b>Меню Code Quest</b>\n\n"
        "• <b>Mini App</b> — квиз с 10 вариантами ответа, грейд выбирается в приложении.\n"
        "• <b>Веб-панель</b> — статистика и управление в браузере по кнопке ниже.\n"
    )
    if _is_group(message):
        await message.reply(
            text,
            reply_markup=group_menu_inline(settings, bot_username=me.username),
        )
    else:
        await message.answer(
            text,
            reply_markup=private_menu_inline(settings),
        )
        await message.answer(
            "Или пользуйтесь клавиатурой внизу:",
            reply_markup=main_menu_keyboard(settings),
        )


@router.message(Command("app"))
async def cmd_app(message: Message, bot: Bot) -> None:
    """Быстрый вход в Mini App."""
    settings = Settings()
    me = await bot.me()
    if _is_group(message):
        text = (
            "Нажмите кнопку «Code Quest — Mini App» — приложение откроется "
            "<b>внутри Telegram</b> (ссылка t.me). "
            "В квизе выберите грейд (junior / middle / senior) и ответьте на вопрос."
        )
        await message.reply(
            text,
            reply_markup=group_menu_inline(settings, bot_username=me.username),
        )
    else:
        text = (
            "Нажмите кнопку — приложение откроется внутри Telegram. "
            "В квизе выберите грейд (junior / middle / senior) и ответьте на вопрос."
        )
        await message.answer(text, reply_markup=main_menu_keyboard(settings))


@router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot) -> None:
    """Краткая справка."""
    settings = Settings()
    me = await bot.me()
    base = str(settings.public_base_url).rstrip("/")
    text = (
        "<b>Справка</b>\n\n"
        "/menu — меню и кнопки\n"
        "/app — открыть Code Quest (Mini App: MCQ-квиз и лидерборд)\n"
        f"Веб-панель: {base}/admin/\n\n"
        "Грейд в квизе задаётся только в Mini App — в боте отдельной команды не требуется.\n\n"
        "В группе боту желательны права администратора, чтобы меню и кнопки отображались стабильно."
    )
    if _is_group(message):
        await message.reply(
            text,
            reply_markup=group_menu_inline(settings, bot_username=me.username),
        )
    else:
        await message.answer(text)
