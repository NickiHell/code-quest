"""Извлечение JSON из ответа LLM (в т.ч. с markdown-ограждением)."""

from __future__ import annotations

import json
from typing import Any, cast


def extract_json_object(text: str) -> dict[str, Any]:
    """Распарсить первый JSON-объект из произвольного текста LLM.

    Стратегия: ищем первую '{' и последнюю '}' — всё между ними и есть JSON.
    Это надёжнее regex по ```...```, который ломается когда модель вставляет
    блок ```python внутрь значения question_text.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        msg = "No JSON object found in model output"
        raise ValueError(msg)
    return cast(dict[str, Any], json.loads(text[start : end + 1]))
