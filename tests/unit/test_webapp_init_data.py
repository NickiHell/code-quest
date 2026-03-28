from __future__ import annotations

import os
import time

import pytest

from src.infrastructure.telegram.webapp_init_data import (
    WebAppInitDataError,
    parse_and_validate_init_data,
)
from tests.support.telegram_init_data import build_valid_init_data


def _bot() -> str:
    return os.environ["BOT_TOKEN"]


def test_parse_valid_init_data() -> None:
    bot = _bot()
    raw = build_valid_init_data(bot_token=bot, user_id=99, username="u1")
    u = parse_and_validate_init_data(raw, bot_token=bot, max_age_seconds=3600)
    assert u.telegram_id == 99
    assert u.username == "u1"


def test_rejects_bad_hash() -> None:
    bot = _bot()
    raw = build_valid_init_data(bot_token=bot)
    prefix = raw.rsplit("&hash=", 1)[0]
    tampered = f"{prefix}&hash=deadbeef"
    with pytest.raises(WebAppInitDataError, match="invalid hash"):
        parse_and_validate_init_data(tampered, bot_token=bot)


def test_rejects_expired_auth_date() -> None:
    bot = _bot()
    old = int(time.time()) - 99999
    raw = build_valid_init_data(bot_token=bot, auth_date=old)
    with pytest.raises(WebAppInitDataError, match="expired"):
        parse_and_validate_init_data(raw, bot_token=bot, max_age_seconds=60)


def test_skips_age_when_max_age_zero() -> None:
    bot = _bot()
    old = int(time.time()) - 99999
    raw = build_valid_init_data(bot_token=bot, auth_date=old)
    u = parse_and_validate_init_data(raw, bot_token=bot, max_age_seconds=0)
    assert u.telegram_id == 424242
