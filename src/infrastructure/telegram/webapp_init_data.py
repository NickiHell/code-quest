from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

from src.entities.telegram_webapp import WebAppUser


class WebAppInitDataError(ValueError):
    pass


def _user_from_json_blob(user_raw: str) -> WebAppUser:
    try:
        user_obj: dict[str, Any] = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise WebAppInitDataError("invalid user json") from exc

    tid = user_obj.get("id")
    if not isinstance(tid, int) or tid <= 0:
        raise WebAppInitDataError("invalid user id")

    username = user_obj.get("username")
    uname = username if isinstance(username, str) and username else None
    fn = user_obj.get("first_name")
    first = fn if isinstance(fn, str) else None
    ln = user_obj.get("last_name")
    last = ln if isinstance(ln, str) else None

    return WebAppUser(
        telegram_id=tid,
        username=uname,
        first_name=first,
        last_name=last,
    )


def parse_and_validate_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> WebAppUser:
    raw = (init_data or "").strip()
    if not raw:
        raise WebAppInitDataError("empty init data")

    pairs_list = parse_qsl(raw, keep_blank_values=True, strict_parsing=False)
    data: dict[str, str] = dict(pairs_list)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise WebAppInitDataError("missing hash")

    check_pairs = sorted(data.items(), key=lambda kv: kv[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in check_pairs)

    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise WebAppInitDataError("invalid hash")

    if max_age_seconds > 0:
        auth_raw = data.get("auth_date")
        if auth_raw is None:
            raise WebAppInitDataError("missing auth_date")
        try:
            auth_ts = int(auth_raw)
        except ValueError as exc:
            raise WebAppInitDataError("invalid auth_date") from exc
        now = int(time.time())
        if now - auth_ts > max_age_seconds:
            raise WebAppInitDataError("init data expired")

    user_raw = data.get("user")
    if not user_raw:
        raise WebAppInitDataError("missing user")

    return _user_from_json_blob(user_raw)
