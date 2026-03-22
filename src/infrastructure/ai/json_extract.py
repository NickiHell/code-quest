"""Извлечение JSON из ответа LLM (в т.ч. с markdown-ограждением)."""

from __future__ import annotations

import json
import re
from typing import Any, cast


def extract_json_object(text: str) -> dict[str, Any]:
    """Распарсить первый JSON-объект из текста."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    return cast(dict[str, Any], json.loads(cleaned))
