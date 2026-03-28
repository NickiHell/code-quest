from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

MCQ_OPTION_COUNT: Final[int] = 5

_LEGACY_GRADE_TO_CANONICAL: Final[dict[str, str]] = {
    "junior": "easy",
    "middle": "medium",
    "senior": "expert",
}


def normalize_quiz_grade(grade: str) -> str:
    g = grade.strip().lower()
    return _LEGACY_GRADE_TO_CANONICAL.get(g, g)


@dataclass(frozen=True)
class QuizQuestionData:
    question_text: str
    options: tuple[str, ...]
    correct_index: int
    grade: str

    def __post_init__(self) -> None:
        if len(self.options) != MCQ_OPTION_COUNT:
            msg = f"Quiz must have exactly {MCQ_OPTION_COUNT} options"
            raise ValueError(msg)
        if not (0 <= self.correct_index < len(self.options)):
            msg = "correct_index out of range"
            raise ValueError(msg)


@dataclass(frozen=True)
class QuizEvaluationResult:
    is_correct: bool
    score: int
    feedback: str


@dataclass(frozen=True)
class QuizQuestionPublic:
    id: int
    question_number: int
    question_text: str
    options: tuple[str, ...]
    grade: str


@dataclass(frozen=True)
class QuizAttempt:
    id: int | None
    user_id: int
    question_id: int
    chosen_index: int
    is_correct: bool
    score: int
    feedback: str
    created_at: datetime
