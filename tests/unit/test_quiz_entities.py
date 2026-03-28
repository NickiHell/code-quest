from __future__ import annotations

import pytest

from src.entities.quiz import (
    MCQ_OPTION_COUNT,
    QuizQuestionData,
    normalize_quiz_grade,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  JUNIOR ", "easy"),
        ("middle", "medium"),
        ("Senior", "expert"),
        ("easy", "easy"),
        ("Expert", "expert"),
        ("medium", "medium"),
        ("unknown_grade", "unknown_grade"),
    ],
)
def test_normalize_quiz_grade_maps_legacy_and_passthrough(raw: str, expected: str) -> None:
    assert normalize_quiz_grade(raw) == expected


@pytest.mark.parametrize("n_opts", [0, 1, 4, 6, 10])
def test_quiz_question_data_rejects_wrong_option_count(n_opts: int) -> None:
    opts = tuple(f"x{i}" for i in range(n_opts))
    with pytest.raises(ValueError, match=str(MCQ_OPTION_COUNT)):
        QuizQuestionData("q", opts, 0, "easy")


def test_quiz_question_data_accepts_five_options_and_valid_index() -> None:
    opts = tuple(f"x{i}" for i in range(MCQ_OPTION_COUNT))
    q = QuizQuestionData("question", opts, 2, "medium")
    assert len(q.options) == MCQ_OPTION_COUNT
    assert q.correct_index == 2
    assert q.grade == "medium"


@pytest.mark.parametrize("bad_index", [-1, 5, 10, 100])
def test_quiz_question_data_rejects_correct_index_out_of_range(bad_index: int) -> None:
    opts = tuple(f"x{i}" for i in range(5))
    with pytest.raises(ValueError, match="correct_index"):
        QuizQuestionData("q", opts, bad_index, "easy")
