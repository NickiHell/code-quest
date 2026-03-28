from __future__ import annotations

import json

import pytest

from src.infrastructure.ai.json_extract import _repair_common_llm_array_glitch, extract_json_object


def test_repair_glitch_replaces_bracket_pattern() -> None:
    raw = '{"a": [1], [2]}'
    assert "], [" in raw
    fixed = _repair_common_llm_array_glitch(raw)
    assert "], [" not in fixed


def test_repair_glitch_noop_when_absent() -> None:
    s = '{"x": 1}'
    assert _repair_common_llm_array_glitch(s) is s


def test_extract_simple_object() -> None:
    text = 'prefix {"k": 1, "b": true} suffix'
    assert extract_json_object(text) == {"k": 1, "b": True}


def test_extract_uses_repair_variant_when_glitch_present() -> None:
    # После repair строка становится валидным JSON (упрощённый пример).
    text = 'x {"opts": ["a"], ["b"]} y'
    # Без repair это не JSON; repair даёт один массив.
    out = extract_json_object(text)
    assert "opts" in out


def test_extract_raises_json_decode_error_when_blob_invalid() -> None:
    text = "{not json}"
    with pytest.raises(json.JSONDecodeError):
        extract_json_object(text)


def test_extract_raises_value_error_when_no_braces() -> None:
    with pytest.raises(ValueError, match="No JSON object"):
        extract_json_object("no braces here")
