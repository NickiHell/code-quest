from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WebAppUser:
    """Идентичность из Mini App после проверки подписи."""

    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
