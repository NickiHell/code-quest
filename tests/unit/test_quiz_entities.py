from __future__ import annotations

import pytest

from src.entities.quiz import (
    MCQ_OPTION_COUNT,
    QuizQuestionData,
    normalize_quiz_grade,
)


def test_normalize_quiz_grade_legacy_and_trim() -> None:
    assert normalize_quiz_grade("  JUNIOR ") == "easy"
    assert normalize_quiz_grade("middle") == "medium"
    assert normalize_quiz_grade("Senior") == "expert"
    assert normalize_quiz_grade("easy") == "easy"


def test_quiz_question_data_validates_option_count() -> None:
    with pytest.raises(ValueError, match=str(MCQ_OPTION_COUNT)):
        QuizQuestionData("q", ("a", "b"), 0, "easy")


def test_quiz_question_data_validates_correct_index() -> None:
    opts = tuple(f"x{i}" for i in range(5))
    with pytest.raises(ValueError, match="correct_index"):
        QuizQuestionData("q", opts, 10, "easy")
