"""Общие промпты и разбор JSON квиза для Ollama и Yandex."""

from __future__ import annotations

import json
import logging
import random
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


_ALLOWED_TOPICS = {"python", "javascript", "algorithms", "data_structures"}

# Конкретные аспекты — Python случайно выберет один и вставит в промпт
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
    "javascript": [
        "closures, scope chain, and the IIFE pattern",
        "prototype chain, Object.create, and class syntax under the hood",
        "event loop, call stack, microtask queue, macrotask queue",
        "Promises: .then/.catch/.finally, Promise.all/race/allSettled/any",
        "async/await and error handling with try/catch",
        "this binding: call, apply, bind, arrow functions vs regular functions",
        "hoisting: var/let/const differences, temporal dead zone",
        "destructuring assignment: arrays, objects, default values, renaming",
        "spread and rest operators (...)",
        "WeakMap, WeakSet, WeakRef and garbage collection implications",
        "Symbol, well-known symbols (Symbol.iterator, Symbol.toPrimitive)",
        "generators and iterators: function*, yield, for...of",
        "Proxy and Reflect APIs",
        "type coercion and equality: == vs ===, truthy/falsy values",
        "Array methods: map, filter, reduce, flat, flatMap, find, findIndex, at",
        "Object methods: Object.keys/values/entries, Object.assign, Object.freeze",
        "module system: ES modules (import/export) vs CommonJS (require)",
        "error types: TypeError, ReferenceError, SyntaxError, RangeError",
        "timers: setTimeout, setInterval, clearTimeout, event loop interaction",
        "Fetch API and XMLHttpRequest: response handling, AbortController",
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
    "junior": "appropriate for a Junior developer — focus on fundamentals and common pitfalls",
    "middle": "appropriate for a Middle developer — include nuanced behaviour or edge cases",
    "senior": "for a Senior developer — deep internals, subtle gotchas, design trade-offs",
}


def build_quiz_generation_prompt(
    grade: str,
    topic: str | None,
    seen_questions: list[str] | None = None,
) -> str:
    """Промпт генерации MCQ — строго Python / алгоритмы / структуры данных."""
    topic_key = (topic or "").strip().lower()
    if topic_key not in _ALLOWED_TOPICS:
        topic_key = "python"

    # Выбираем один конкретный аспект на стороне Python — так промпт остаётся коротким
    # и модели не нужно самой принимать решение о разнообразии
    aspect = random.choice(_TOPIC_ASPECTS[topic_key])
    grade_hint = _GRADE_HINTS.get(grade.lower(), f"grade level: {grade}")

    avoid_block = ""
    if seen_questions:
        items = "\n".join(f"- {q}" for q in seen_questions)
        avoid_block = f"\nDo NOT repeat or rephrase these already-asked questions:\n{items}\n"

    return (
        "You are a Python interview expert. Generate ONE multiple-choice question in Russian.\n\n"
        f"Topic: {aspect}\n"
        f"Level: {grade_hint}\n"
        f"{avoid_block}\n"
        "Rules:\n"
        "- All text (question and options) must be in Russian.\n"
        "- Make the question specific and non-trivial (no 'what does len() do?' style).\n"
        "- Make at least 3 wrong options plausible (common misconceptions or subtle differences).\n"
        "- If useful, include a short code snippet in question_text (no markdown fences).\n\n"
        "Respond with ONLY this JSON, no extra text:\n"
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
    """Промпт объяснения выбора по-русски."""
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

    if not q or not isinstance(opts, list) or not (2 <= len(opts) <= 8):
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
