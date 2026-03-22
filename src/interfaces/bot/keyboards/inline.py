"""Inline-клавиатуры: Mini App (внутри Telegram) и ссылка на веб-админку."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.core.config import Settings


def group_menu_inline(settings: Settings) -> InlineKeyboardMarkup:
    """Меню для групп: ссылки + веб-панель.

    Кнопка ``web_app`` во встроенной клавиатуре в группах/каналах запрещена Bot API
    (только личка с ботом) — иначе ``BUTTON_TYPE_INVALID``. В группе используем
    обычную ссылку ``url`` на тот же HTTPS-адрес Mini App.
    """
    base = str(settings.public_base_url).rstrip("/")
    webapp_url = str(settings.webapp_url)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Code Quest — Mini App",
                    url=webapp_url,
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
