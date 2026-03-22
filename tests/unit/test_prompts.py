"""Тесты разбора JSON квиза."""

from __future__ import annotations

import pytest

from src.infrastructure.ai.prompts import parse_quiz_json


def test_parse_quiz_json_valid() -> None:
    raw = (
        '{"question_text": "Q?", "options": ["a","b","c","d","e","f","g","h","i","j"], '
        '"correct_index": 2, "grade": "junior"}'
    )
    q = parse_quiz_json(raw, default_grade="middle")
    assert q.question_text == "Q?"
    assert len(q.options) == 10
    assert q.correct_index == 2
    assert q.grade == "junior"


def test_parse_quiz_json_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_quiz_json("not json", default_grade="junior")
