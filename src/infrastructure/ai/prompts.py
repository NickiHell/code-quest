"""Общие промпты и разбор JSON квиза для Ollama и Yandex."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.entities.quiz import QuizQuestionData
from src.infrastructure.ai.json_extract import extract_json_object

logger = logging.getLogger(__name__)


def build_evaluate_code_prompt(code: str, task_description: str) -> str:
    """Промпт для ревью кода."""
    return (
        f"You are a strict code reviewer.\n\n"
        f"Task:\n{task_description}\n\n"
        f"Submitted code:\n```\n{code}\n```\n\n"
        f"Briefly evaluate correctness, style, and edge cases."
    )


_ALLOWED_TOPICS = {"python", "algorithms", "data_structures"}

_TOPIC_LABELS: dict[str, str] = {
    "python": "Python programming language (syntax, built-ins, stdlib, idioms)",
    "algorithms": "classic algorithms (sorting, searching, graph, dynamic programming, greedy)",
    "data_structures": "data structures (arrays, linked lists, trees, graphs, heaps, hash tables)",
}


def build_quiz_generation_prompt(grade: str, topic: str | None) -> str:
    """Промпт генерации MCQ — строго Python / алгоритмы / структуры данных."""
    topic_key = (topic or "").strip().lower()
    if topic_key not in _ALLOWED_TOPICS:
        topic_key = "python"
    topic_desc = _TOPIC_LABELS[topic_key]
    return (
        "You are an expert Python interviewer. "
        f"Produce ONE multiple-choice question strictly about {topic_desc} "
        f"for a software engineer at grade level: {grade}.\n"
        "IMPORTANT: the question MUST be about Python or algorithms/data structures only. "
        "Do NOT ask about other languages, frameworks, or unrelated topics.\n"
        "Return ONLY a JSON object with these keys:\n"
        '  "question_text": string (in Russian),\n'
        '  "options": array of exactly 10 distinct strings (in Russian, each plausible),\n'
        '  "correct_index": integer 0-9 (index of the single correct option),\n'
        f'  "grade": "{grade}".\n'
        "No markdown, no explanation — raw JSON only."
    )


def build_quiz_explain_prompt(
    question_text: str,
    options: tuple[str, ...],
    correct_index: int,
    chosen_index: int,
) -> str:
    """Промпт объяснения выбора по-русски."""
    opts_lines = "\n".join(f"{i}. {options[i]}" for i in range(10))
    return (
        "Ты ментор по программированию. Пользователь выбрал один вариант ответа.\n"
        f"Вопрос:\n{question_text}\n\n"
        f"Варианты:\n{opts_lines}\n\n"
        f"Правильный индекс: {correct_index}. Выбран индекс: {chosen_index}.\n"
        "Дай 2-4 предложения по-русски: почему ответ верный или неверный, "
        "без выдумывания фактов."
    )


def parse_quiz_json(raw: str, *, default_grade: str) -> QuizQuestionData:
    """Разобрать ответ модели в QuizQuestionData."""
    try:
        data = extract_json_object(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.exception("Failed to parse quiz JSON: %s", raw[:500])
        msg = "Invalid JSON from model"
        raise ValueError(msg) from exc

    return quiz_data_from_dict(data, default_grade=default_grade)


def quiz_data_from_dict(data: dict[str, Any], *, default_grade: str) -> QuizQuestionData:
    """Проверить структуру dict и собрать QuizQuestionData."""
    q = str(data.get("question_text", "")).strip()
    opts = data.get("options")
    ci = data.get("correct_index")
    g = str(data.get("grade", default_grade)).strip()

    if not q or not isinstance(opts, list) or len(opts) != 10:
        msg = "Invalid question shape from model"
        raise ValueError(msg)
    options_norm = tuple(str(x).strip() for x in opts)
    if not isinstance(ci, int) or not (0 <= ci <= 9):
        msg = "Invalid correct_index from model"
        raise ValueError(msg)

    return QuizQuestionData(
        question_text=q,
        options=options_norm,
        correct_index=ci,
        grade=g,
    )
