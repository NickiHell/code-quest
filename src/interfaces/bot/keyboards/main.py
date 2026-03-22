"""Reply keyboards for the Telegram bot."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from src.core.config import Settings


def main_menu_keyboard(settings: Settings | None = None) -> ReplyKeyboardMarkup:
    """Primary menu with a Mini App launch button."""
    cfg = settings or Settings()
    webapp = WebAppInfo(url=str(cfg.webapp_url))
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Mini App: Code Quest", web_app=webapp)]],
        resize_keyboard=True,
    )
