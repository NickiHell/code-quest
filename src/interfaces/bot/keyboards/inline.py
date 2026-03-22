"""Inline-клавиатуры: Mini App (внутри Telegram) и ссылка на веб-админку."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.core.config import Settings


def group_menu_inline(settings: Settings, *, bot_username: str | None) -> InlineKeyboardMarkup:
    """Меню для групп: Mini App + веб-панель.

    Кнопка ``web_app`` во встроенной клавиатуре в группах запрещена Bot API
    (``BUTTON_TYPE_INVALID``). Вместо прямого ``https`` на страницу (открывает
    внешний браузер) используем ``https://t.me/<bot>?startapp`` — клиент Telegram
    запускает Mini App из BotFather **внутри** приложения.

    Если у бота нет ``@username`` (редко), fallback на ``webapp_url`` (снова браузер).
    """
    base = str(settings.public_base_url).rstrip("/")
    webapp_url = str(settings.webapp_url)
    if bot_username:
        uname = bot_username.lstrip("@")
        mini_open_url = f"https://t.me/{uname}?startapp"
    else:
        mini_open_url = webapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Code Quest — Mini App",
                    url=mini_open_url,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Веб: статистика и управление",
                    url=f"{base}/admin/",
                ),
            ],
        ],
    )


def private_menu_inline(settings: Settings) -> InlineKeyboardMarkup:
    """Дублирует ссылки для лички (в дополнение к reply-клавиатуре)."""
    base = str(settings.public_base_url).rstrip("/")
    webapp_url = str(settings.webapp_url)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Code Quest — Mini App",
                    web_app=WebAppInfo(url=webapp_url),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Веб: статистика и управление",
                    url=f"{base}/admin/",
                ),
            ],
        ],
    )
