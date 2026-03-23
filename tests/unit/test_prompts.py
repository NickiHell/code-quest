"""Тесты разбора JSON квиза."""

from __future__ import annotations

import pytest

from src.infrastructure.ai.prompts import parse_quiz_json


def test_parse_quiz_json_valid() -> None:
    raw = (
        '{"question_text": "Q?", "options": ["a","b","c","d","e"], '
        '"correct_index": 2, "grade": "easy"}'
    )
    q = parse_quiz_json(raw, default_grade="medium")
    assert q.question_text == "Q?"
    assert len(q.options) == 5
    assert q.correct_index == 2
    assert q.grade == "easy"


def test_parse_quiz_json_normalizes_legacy_grade() -> None:
    raw = (
        '{"question_text": "Q?", "options": ["a","b","c","d","e"], '
        '"correct_index": 2, "grade": "junior"}'
    )
    q = parse_quiz_json(raw, default_grade="medium")
    assert q.grade == "easy"


def test_parse_quiz_json_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_quiz_json("not json", default_grade="easy")


def test_parse_quiz_json_requires_five_options() -> None:
    raw = '{"question_text": "Q?", "options": ["a","b"], "correct_index": 0, "grade": "easy"}'
    with pytest.raises(ValueError, match="Invalid"):
        parse_quiz_json(raw, default_grade="easy")
