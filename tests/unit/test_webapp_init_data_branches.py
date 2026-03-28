from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from src.infrastructure.telegram.webapp_init_data import (
    WebAppInitDataError,
    _user_from_json_blob,
    parse_and_validate_init_data,
)
from tests.support.telegram_init_data import build_valid_init_data


def test_user_from_json_invalid_json() -> None:
    with pytest.raises(WebAppInitDataError, match="invalid user json"):
        _user_from_json_blob("{not json")


def test_user_from_json_bad_id() -> None:
    with pytest.raises(WebAppInitDataError, match="invalid user id"):
        _user_from_json_blob(json.dumps({"id": "x"}))


def test_parse_empty_init_data() -> None:
    with pytest.raises(WebAppInitDataError, match="empty"):
        parse_and_validate_init_data("", bot_token="t" * 20, max_age_seconds=0)


def test_parse_missing_hash() -> None:
    bot = "1234567890:ABCDEF-test"
    with pytest.raises(WebAppInitDataError, match="missing hash"):
        parse_and_validate_init_data("auth_date=1", bot_token=bot, max_age_seconds=0)


def test_parse_missing_user_after_valid_hash() -> None:
    bot = "1234567890:ABCDEF-test"
    # Подпись только для auth_date (без user): hash валиден, поля user нет.
    pairs = {"auth_date": str(9999999999)}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot.encode(), hashlib.sha256).digest()
    sig = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    raw = urlencode({**pairs, "hash": sig})
    with pytest.raises(WebAppInitDataError, match="missing user"):
        parse_and_validate_init_data(raw, bot_token=bot, max_age_seconds=0)


def test_parse_skips_age_when_max_age_zero() -> None:
    bot = "1234567890:ABCDEF-test"
    raw = build_valid_init_data(bot_token=bot, auth_date=1)
    u = parse_and_validate_init_data(raw, bot_token=bot, max_age_seconds=0)
    assert u.telegram_id == 424242


def test_parse_rejects_non_integer_auth_date() -> None:
    bot = "1234567890:ABCDEF-test"
    # Валидный hash при auth_date нечисла — ветка int() в parse.
    user_json = '{"id":1,"first_name":"A"}'
    pairs = {"auth_date": "not-int", "user": user_json}
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    sk = hmac.new(b"WebAppData", bot.encode(), hashlib.sha256).digest()
    sig = hmac.new(sk, check.encode(), hashlib.sha256).hexdigest()
    bad = urlencode({**pairs, "hash": sig})
    with pytest.raises(WebAppInitDataError, match="auth_date"):
        parse_and_validate_init_data(bad, bot_token=bot, max_age_seconds=3600)
