from __future__ import annotations

import json
import logging
import random
from typing import Any, Final

from src.entities.quiz import MCQ_OPTION_COUNT, QuizQuestionData, normalize_quiz_grade
from src.infrastructure.ai.json_extract import extract_json_object

logger = logging.getLogger(__name__)
_JSON_LOG_PREVIEW_LEN: Final[int] = 400

_SEEN_QUESTION_SKIP_SUBSTRINGS: Final[tuple[str, ...]] = (
    "контр-бпл",
    "контр бпл",
    "контрбпл",
    "противодрон",
    "counter-uas",
    "counter uas",
    "радиопомех",
)

QUIZ_GENERATION_SYSTEM_INSTRUCTIONS: Final[str] = (
    "Ты помощник образовательного приложения с тестами (школьники, студенты, курсы). "
    "На каждый запрос отвечай только одним JSON-объектом в точности по схеме из запроса. "
    "Не отказывайся от безопасных учебных тем из запроса; не выводи текст вне JSON."
)


def _filter_seen_questions_for_prompt(seen: list[str] | None) -> list[str] | None:
    if not seen:
        return None
    out: list[str] = []
    for q in seen:
        low = q.lower()
        if any(s in low for s in _SEEN_QUESTION_SKIP_SUBSTRINGS):
            continue
        out.append(q)
    return out or None


def build_evaluate_code_prompt(code: str, task_description: str) -> str:
    return (
        f"You are a strict code reviewer.\n\n"
        f"Task:\n{task_description}\n\n"
        f"Submitted code:\n```\n{code}\n```\n\n"
        f"Briefly evaluate correctness, style, and edge cases."
    )


_ALLOWED_TOPICS = frozenset({"python", "algorithms", "data_structures"})

_TOPIC_ASPECTS: dict[str, list[str]] = {
    "python": [
        "built-in functions: len, map, filter, zip, enumerate, sorted, any, all, min, max",
        "list/dict/set comprehensions and generator expressions",
        "string methods and f-string formatting",
        "itertools module: chain, product, combinations, permutations, groupby",
        "functools module: reduce, partial, lru_cache, wraps",
        "collections module: defaultdict, Counter, deque, OrderedDict, namedtuple",
        "decorators and closures",
        "context managers: with statement, __enter__/__exit__, contextlib",
        "exception handling: try/except/else/finally, exception hierarchy, raise from",
        "dunder methods: __repr__, __str__, __eq__, __hash__, __len__, __iter__, __getitem__",
        "type hints and typing module: Optional, Union, TypeVar, Protocol, Literal",
        "async/await, asyncio event loop, coroutines, gather, tasks",
        "threading and multiprocessing: GIL, locks, queues, process pools",
        "descriptors, properties, classmethod, staticmethod",
        "import system: __init__.py, relative imports, __all__, sys.modules",
        "CPython internals: bytecode, dis module, __slots__, reference counting",
        "regex: re module, groups, lookahead, flags, search vs match vs fullmatch",
        "pathlib and file I/O",
    ],
    "algorithms": [
        "sorting algorithms: bubble, insertion, merge, quicksort — complexity and stability",
        "binary search and its variants (left/right boundary, rotated array)",
        "two-pointer and sliding window techniques",
        "dynamic programming: memoization vs tabulation, state transitions",
        "classic DP problems: knapsack, LCS, LIS, edit distance, coin change",
        "greedy algorithms: interval scheduling, activity selection",
        "backtracking: N-queens, permutations, subsets",
        "divide and conquer: merge sort, binary search recurrence, master theorem",
        "graph traversal: BFS, DFS, topological sort, cycle detection",
        "shortest path algorithms: Dijkstra, Bellman-Ford, Floyd-Warshall",
        "minimum spanning tree: Kruskal, Prim, union-find",
        "bit manipulation: XOR tricks, popcount, bit masking",
        "string algorithms: KMP, Z-function, Rabin-Karp hashing",
        "computational complexity: P vs NP, amortised analysis",
        "randomised algorithms: reservoir sampling, Fisher-Yates shuffle",
    ],
    "data_structures": [
        "dynamic arrays: resizing strategy and amortised O(1) append",
        "singly and doubly linked lists: insert, delete, reverse, cycle detection",
        "stack and queue: array-based vs linked, monotonic stack, deque",
        "binary tree traversals: in-order, pre-order, post-order, level-order",
        "BST: insert, delete, find successor, balancing (AVL rotations)",
        "heaps: max-heap, min-heap, heapify O(n), priority queue operations",
        "hash tables: collision resolution, chaining, open addressing, load factor",
        "tries: insert, search, prefix counting",
        "graphs: adjacency list vs matrix, weighted vs unweighted",
        "union-find (DSU): union by rank, path compression",
        "segment tree: range sum/min queries, point updates",
        "Fenwick tree (BIT): prefix sums, point updates",
        "LRU cache: combining hash map and doubly-linked list",
        "bloom filter: probabilistic membership, false positive rate",
    ],
}

_GRADE_HINTS: dict[str, str] = {
    "easy": (
        "лёгкий уровень: как для человека, который только познакомился с темой. "
        "Одно простое понятие или факт, без ловушек и без многоходовых рассуждений"
    ),
    "medium": "средний уровень: нюансы и типичные заблуждения",
    "expert": "экспертный уровень: глубина, тонкости, неочевидные детали",
}


def build_quiz_generation_prompt(
    grade: str,
    topic: str | None,
    seen_questions: list[str] | None = None,
) -> str:
    topic_key = (topic or "").strip().lower()
    if topic_key not in _ALLOWED_TOPICS:
        topic_key = "python"

    aspect = random.choice(_TOPIC_ASPECTS[topic_key])  # nosec B311  # noqa: S311
    canon = normalize_quiz_grade(grade)
    grade_hint = _GRADE_HINTS.get(canon, f"сложность: {grade}")

    if canon == "easy":
        level_rules = (
            "- EASY: вопрос должен быть по ощущениям «простым» — его может ответить тот, кто "
            "прочитал вводный материал по теме. Ровно одна идея, без цепочки шагов и без "
            "разбора краевых случаев.\n"
            "- Неправильные варианты должны отличаться от верного заметно для новичка "
            "(типичная путаница имён или смыслов — но не четыре одинаково правдоподобных "
            "«экспертных» ответа).\n"
            "- Если выбранный аспект темы звучит сложно, сформулируй вопрос только про самое "
            "элементарное определение, назначение или факт из этой области.\n"
            "- Допускаются прямолинейные и «учебниковые» формулировки — не усложняй ради "
            "интереса.\n"
            "- Без длинного кода в тексте вопроса; если нужен код — одна короткая строка и "
            "вопрос только про самое прямое чтение результата.\n"
        )
    else:
        level_rules = (
            "- Сделай вопрос конкретным и нетривиальным (не стиль «что делает len()?»).\n"
            "- Четыре неверных ответа — правдоподобные, с типичными заблуждениями или тонкими "
            "различиями, где уместно.\n"
        )

    seen_safe = _filter_seen_questions_for_prompt(seen_questions)
    avoid_block = ""
    if seen_safe:
        items = "\n".join(f"- {q}" for q in seen_safe)
        avoid_block = f"\nDo NOT repeat or rephrase these already-asked questions:\n{items}\n"

    code_hint = (
        "- If useful, include a short code snippet in question_text (no markdown fences).\n\n"
        if canon != "easy"
        else "\n"
    )

    return (
        "You are a quiz expert. Generate ONE multiple-choice question in Russian.\n\n"
        f"Topic: {aspect}\n"
        f"Level: {grade_hint}\n"
        f"{avoid_block}\n"
        "Rules:\n"
        "- All text (question and options) must be in Russian.\n"
        f"{level_rules}"
        "- You MUST output exactly 5 options: one correct and four wrong answers.\n"
        '- The "options" field MUST be a single JSON array of exactly five strings, '
        'e.g. ["a","b","c","d","e"] — do NOT split into multiple arrays.\n'
        f"{code_hint}"
        "Respond with ONLY one JSON object, no markdown code fences, no text after the closing }:\n"
        '{"question_text": "...", '
        '"options": ["opt0", "opt1", "opt2", "opt3", "opt4"], '
        f'"correct_index": 0, "grade": "{grade}"}}'
    )


def build_quiz_explain_prompt(
    question_text: str,
    options: tuple[str, ...],
    correct_index: int,
    chosen_index: int,
) -> str:
    opts_lines = "\n".join(f"{i}. {options[i]}" for i in range(len(options)))
    return (
        "Ты ментор по программированию. Пользователь выбрал один вариант ответа.\n"
        f"Вопрос:\n{question_text}\n\n"
        f"Варианты:\n{opts_lines}\n\n"
        f"Правильный индекс: {correct_index}. Выбран индекс: {chosen_index}.\n"
        "Дай 2-4 предложения по-русски: почему ответ верный или неверный, "
        "без выдумывания фактов."
    )


def parse_quiz_json(raw: str, *, default_grade: str) -> QuizQuestionData:
    try:
        data = extract_json_object(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        preview = raw[:_JSON_LOG_PREVIEW_LEN] + ("…" if len(raw) > _JSON_LOG_PREVIEW_LEN else "")
        logger.warning("Failed to parse quiz JSON (%s): %s", exc, preview)
        msg = "Invalid JSON from model"
        raise ValueError(msg) from exc

    return quiz_data_from_dict(data, default_grade=default_grade)


def quiz_data_from_dict(data: dict[str, Any], *, default_grade: str) -> QuizQuestionData:
    q = str(data.get("question_text", "")).strip()
    opts = data.get("options")
    ci = data.get("correct_index")
    raw_g = str(data.get("grade", default_grade)).strip()
    g = normalize_quiz_grade(raw_g)

    if not q or not isinstance(opts, list) or len(opts) != MCQ_OPTION_COUNT:
        msg = "Invalid question shape from model"
        raise ValueError(msg)
    options_norm = tuple(str(x).strip() for x in opts)
    if not isinstance(ci, int) or not (0 <= ci < len(options_norm)):
        msg = "Invalid correct_index from model"
        raise ValueError(msg)

    return QuizQuestionData(
        question_text=q,
        options=options_norm,
        correct_index=ci,
        grade=g,
    )
