from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode


def build_valid_init_data(
    *,
    bot_token: str,
    user_id: int = 424242,
    username: str | None = "testuser",
    auth_date: int | None = None,
) -> str:
    """Вернуть query string с корректным hash (как в Mini App)."""
    ad = auth_date if auth_date is not None else int(time.time())
    user_obj: dict[str, Any] = {
        "id": user_id,
        "first_name": "Test",
    }
    if username:
        user_obj["username"] = username
    user_json = json.dumps(user_obj, separators=(",", ":"))
    pairs = {
        "auth_date": str(ad),
        "query_id": "AA",
        "user": user_json,
    }
    check_pairs = sorted(pairs.items(), key=lambda kv: kv[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in check_pairs)
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    out = dict(pairs)
    out["hash"] = sig
    return urlencode(out)
