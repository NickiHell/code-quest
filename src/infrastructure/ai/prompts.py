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


_ALLOWED_TOPICS = {
    "python",
    "javascript",
    "algorithms",
    "data_structures",
    "chess",
    "go",
    "land_navigation",
    "fishing",
    "car_repair",
}

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
    "chess": [
        "piece movement rules: how each piece moves and captures",
        "special moves: castling (kingside/queenside), en passant, pawn promotion",
        "check, checkmate, and stalemate: definitions and examples",
        "basic openings: e4/e5, d4/d5, Sicilian Defence, French Defence, Ruy López",
        "opening principles: center control, piece development, king safety",
        "tactical motifs: fork, pin, skewer, discovered attack, double check",
        "combination patterns: back-rank mate, smothered mate, Greco's mate",
        "endgame fundamentals: king and pawn endings, opposition, key squares",
        "rook endgames: Lucena position, Philidor position",
        "piece values and exchange: when to trade pieces",
        "pawn structure: isolated pawn, doubled pawn, passed pawn, pawn chain",
        "positional concepts: outpost, weak square, open file, bishop pair",
        "notation: algebraic notation, reading and writing chess moves",
        "time control and clock rules: touch-move, illegal move penalties",
        "draw conditions: threefold repetition, fifty-move rule, insufficient material",
        "FIDE rating system: Elo calculation, categories (CM, FM, IM, GM)",
    ],
    "go": [
        "basic rules: stone placement, liberties, capture",
        "ko rule: why it exists and how it works",
        "territory and scoring: area scoring vs territory scoring, komi",
        "life and death: two eyes, unconditional life, seki (mutual life)",
        "corner, side, and center: relative importance of board areas",
        "joseki: common corner sequences and their purpose",
        "fuseki: whole-board opening strategy, common opening patterns",
        "handicap stones: how they work and their strategic implications",
        "connectivity: cutting and connecting groups",
        "influence and thickness: building influence vs territory",
        "tesuji: tactical tricks — ladder, net (geta), snapback, squeeze",
        "ladder (shicho): what it is, when it works, ladder breakers",
        "net (geta): how to capture stones with a net",
        "reducing and invading: when to reduce vs invade opponent's moyo",
        "endgame (yose): sente vs gote moves, counting endgame value",
        "rank system: kyu and dan ranks, online rating systems (ELO, Glicko)",
    ],
    "land_navigation": [
        "map reading: scale, legend, contour lines, relief shading",
        "compass use: magnetic north vs true north, declination correction",
        "orienteering symbols: vegetation, water, buildings, paths (IOF symbols)",
        "bearing and azimuth: taking and following a bearing",
        "resection and triangulation: finding position from known landmarks",
        "pace counting and distance estimation on terrain",
        "GPS vs map-and-compass: when to trust each, limitations",
        "terrain association: matching map to ground, attack points, catching features",
        "route choice: considering elevation, vegetation, linear features",
        "night navigation: limited visibility, headlamp use, pacing",
        "weather impact on terrain: fog, rain, snow, river crossings",
        "safety: telling someone your plan, emergency kit, SOS",
        "MGRS/UTM coordinates: reading grid references",
        "orienteering competition: start procedure, punching controls, course types",
        "star navigation basics: finding Polaris, Southern Cross (overview)",
        "dead reckoning: errors accumulate, when to reset position",
    ],
    "fishing": [
        "freshwater vs saltwater species and habitats",
        "rod types: spinning, casting, fly, feeder — when to use which",
        "reels: spinning vs baitcasting, drag system, line capacity",
        "fishing line: monofilament vs fluorocarbon vs braided — pros and cons",
        "hooks: sizes, barbed vs barbless, circle hooks",
        "natural baits vs artificial lures: worms, minnows, soft plastics, crankbaits",
        "fly fishing: dry fly, nymph, streamer, matching the hatch",
        "ice fishing: safety on ice, augers, tip-ups",
        "reading water: depth, structure, current seams, eddies",
        "seasons and fish behaviour: spawning, feeding windows",
        "knots: improved clinch, Palomar, uni knot, loop knots",
        "regulations: catch limits, size limits, closed seasons, licences",
        "catch and release: handling fish, barotrauma in deep water",
        "boat fishing basics: anchoring, trolling, fish finders (overview)",
        "filleting and food safety: freshness, ice, parasites in raw fish",
    ],
    "car_repair": [
        "engine basics: four-stroke cycle, ignition, fuel injection vs carburetor",
        "cooling system: thermostat, radiator, coolant types, overheating diagnosis",
        "lubrication: oil grades, viscosity, change intervals, filter",
        "brakes: disc vs drum, pads, rotors, brake fluid, ABS basics",
        "suspension: struts, shocks, springs, alignment symptoms",
        "electrical: battery, alternator, starter, fuses, relays",
        "tires: pressure, tread depth, rotation, balancing, TPMS",
        "OBD-II: reading codes, common P-codes meaning (overview)",
        "timing belt vs chain: replacement intervals, interference engines",
        "transmission: manual vs automatic fluid, clutch wear signs",
        "exhaust: catalytic converter, lambda sensor, emissions",
        "HVAC: AC recharge, cabin filter, defrost",
        "DIY safety: jack stands, torque wrench, ESD when disconnecting battery",
        "hybrid and EV basics: high voltage safety, 12V battery, charging",
        "common tools: socket sets, torque specs, thread repair (helicoil overview)",
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
        "You are a quiz expert. Generate ONE multiple-choice question in Russian.\n\n"
        f"Topic: {aspect}\n"
        f"Level: {grade_hint}\n"
        f"{avoid_block}\n"
        "Rules:\n"
        "- All text (question and options) must be in Russian.\n"
        "- Make the question specific and non-trivial (no 'what does len() do?' style).\n"
        "- You MUST output exactly 5 options: one correct and four plausible wrong answers "
        "(common misconceptions or subtle differences).\n"
        '- The "options" field MUST be a single JSON array of exactly five strings, '
        'e.g. ["a","b","c","d","e"] — do NOT split into multiple arrays.\n'
        "- If useful, include a short code snippet in question_text (no markdown fences).\n\n"
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
        preview = raw[:400] + ("…" if len(raw) > 400 else "")
        logger.warning("Failed to parse quiz JSON (%s): %s", exc, preview)
        msg = "Invalid JSON from model"
        raise ValueError(msg) from exc

    return quiz_data_from_dict(data, default_grade=default_grade)


def quiz_data_from_dict(data: dict[str, Any], *, default_grade: str) -> QuizQuestionData:
    """Проверить структуру dict и собрать QuizQuestionData."""
    q = str(data.get("question_text", "")).strip()
    opts = data.get("options")
    ci = data.get("correct_index")
    g = str(data.get("grade", default_grade)).strip()

    if not q or not isinstance(opts, list) or len(opts) != 5:
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
