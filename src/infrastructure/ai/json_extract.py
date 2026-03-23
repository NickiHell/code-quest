"""Извлечение JSON из ответа LLM (в т.ч. с markdown-ограждением)."""

from __future__ import annotations

import json
from typing import Any, cast


def _repair_common_llm_array_glitch(fragment: str) -> str:
    """Иногда модель пишет \"options\": [\"a\"], [\"b\"] вместо одного массива."""
    if "], [" not in fragment:
        return fragment
    return fragment.replace("], [", ", ")


def extract_json_object(text: str) -> dict[str, Any]:
    """Распарсить первый JSON-объект из произвольного текста LLM.

    Стратегия: ищем первую '{' и последнюю '}' — всё между ними и есть JSON.
    Это надёжнее regex по ```...```, который ломается когда модель вставляет
    блок ```python внутрь значения question_text.
    """
    variants = [text]
    if "], [" in text:
        variants.append(_repair_common_llm_array_glitch(text))
    last_err: json.JSONDecodeError | None = None
    for raw in variants:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            continue
        blob = raw[start : end + 1]
        try:
            return cast(dict[str, Any], json.loads(blob))
        except json.JSONDecodeError as exc:
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    msg = "No JSON object found in model output"
    raise ValueError(msg)
