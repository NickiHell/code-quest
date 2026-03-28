from __future__ import annotations

from urllib.parse import urlparse

from src.core.config import Settings
from src.interfaces.bot.keyboards.inline import group_menu_inline, private_menu_inline
from src.interfaces.bot.keyboards.main import main_menu_keyboard


def _cfg() -> Settings:
    return Settings(
        secret_key="x" * 16,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        yandex_folder_id="f",
        yandex_auth="k",
    )


def test_group_menu_inline_with_username_uses_tme() -> None:
    kb = group_menu_inline(_cfg(), bot_username="@mybot")
    u = urlparse(kb.inline_keyboard[0][0].url)
    assert u.scheme == "https" and u.netloc == "t.me" and u.path == "/mybot"


def test_group_menu_inline_without_username_falls_back() -> None:
    kb = group_menu_inline(_cfg(), bot_username=None)
    assert kb.inline_keyboard[0][0].url.startswith("https://")


def test_private_menu_inline_has_web_app() -> None:
    cfg = _cfg()
    kb = private_menu_inline(cfg)
    btn = kb.inline_keyboard[0][0]
    assert btn.web_app is not None
    assert btn.web_app.url == str(cfg.webapp_url)


def test_main_menu_keyboard_uses_passed_settings() -> None:
    kb = main_menu_keyboard(_cfg())
    assert kb.keyboard[0][0].web_app is not None
    assert "Mini App" in kb.keyboard[0][0].text
