"""Промпты и разбор JSON квиза."""

from __future__ import annotations

import json
import logging
import random
from typing import Any, Final

from src.entities.quiz import MCQ_OPTION_COUNT, QuizQuestionData, normalize_quiz_grade
from src.infrastructure.ai.json_extract import extract_json_object

logger = logging.getLogger(__name__)
_JSON_LOG_PREVIEW_LEN: Final[int] = 400


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
    "uavs",
    "military_tactics",
    "reb",
    "lrs",
    "flight_controllers",
    "aerodynamics",
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
    "uavs": [
        "multicopter vs fixed-wing UAV: thrust, stall, endurance trade-offs",
        "propeller and motor basics: KV, pitch, ESC, LiPo cell count and C-rating",
        "flight modes: GPS hold, attitude, altitude, return-to-home (RTH)",
        "sensors: IMU, barometer, magnetometer, GPS — what each corrects",
        "geofencing, no-fly zones, altitude limits in civil aviation",
        "registration and licensing (overview): when UAV requires pilot credentials",
        "battery safety: storage voltage, charging, fire risk, damaged cells",
        "link and control: RC vs digital link, failsafe behaviour, loss of signal",
        "camera gimbals: 2-axis vs 3-axis, rolling shutter vs global shutter",
        "mission planning: waypoints, survey grids, overlap in photogrammetry",
        "weather limits: wind, rain, gusts vs UAV class",
        "payload weight and centre of gravity effects on flight",
        "FPV basics: latency, goggles, OSD, line-of-sight rules",
        "detect-and-avoid concepts (overview): ADS-B, sense, BVLOS research",
        "counter-UAS and legal interception (high-level regulatory concepts only)",
        "agricultural and inspection use cases: multispectral, thermal (overview)",
    ],
    "military_tactics": [
        "levels of war: strategic, operational, tactical — definitions and examples",
        "offensive vs defensive operations: when each is appropriate",
        "terrain: key terrain, observation, fields of fire, cover vs concealment",
        "manoeuvre warfare vs attrition — core ideas",
        "flanking, envelopment, frontal attack — classic forms of manoeuvre",
        "defence in depth vs linear defence — trade-offs",
        "ambush and counter-ambush: principles (historical examples)",
        "reconnaissance and security: screen, guard, cover in movement",
        "combined arms: infantry, artillery, armour coordination (conceptual)",
        "urban operations: challenges of built-up areas (generic principles)",
        "amphibious and river crossing — planning factors (overview)",
        "logistics and sustainment: why they constrain tactical options",
        "command and control: span of control, mission command (conceptual)",
        "historical battles as case studies: Cannae, encirclement, Fabian strategy (facts only)",
        "small-unit tactics: fire and movement, bounding overwatch (generic theory)",
        "NATO vs Warsaw Pact doctrinal differences during Cold War (high-level)",
        "asymmetric warfare: guerrilla vs conventional — definitions, not how-to",
    ],
    "reb": [
        "РЭБ: задачи подавления, маскировки, разведки в СВЧ-диапазоне (общетеоретически)",
        "виды воздействия: активное подавление, пассивная маскировка, имитация (принципы)",
        "помехи по носителю: непрерывная, импульсная, модулированная — идея и применение",
        "подавление каналов связи и наведения: что обычно защищают (концептуально)",
        "радиоразведка: перехват, пеленгация, классификация излучений (уровень учебника)",
        "ЭПР и маскировка: снижение заметности для РЛС (общие принципы)",
        "ECCM: защита от помех, смена частоты, узкие лучи, кодирование (идеи)",
        "спектр и полосы: HF/VHF/UHF/SHF — где что применяют в общих чертах",
        "бортовые и наземные комплексы РЭБ: роли в системе (без ТТХ конкретных изделий)",
        "правовые рамки гражданского применения: ограничения на глушение связи",
        "электромагнитная совместимость и уязвимость аппаратуры (общие понятия)",
        "космический и наземный SIGINT — различие задач (обзорно)",
        "кибер-РЭБ vs классическая РЭБ — границы терминов",
        "исторические этапы: от мешков с фольгой до современных комплексов (факты)",
        "безопасность персонала: излучение, дальность, зоны ограничения (обучающий уровень)",
        "этика и закон: только образовательный контент, без инструкций по изготовлению помех",
    ],
    "lrs": [
        "радиолокация: импульсный режим, дальность по задержке сигнала",
        "доплеровский сдвиг частоты и измерение скорости цели",
        "разрешающая способность по дальности и по углу (принципы)",
        "диаграмма направленности антенны, ширина луча, усиление",
        "обзорные и целеуказания РЛС: различие ролей в системе ПВО/навигации (концептуально)",
        "ФАР: фазированная антенная решётка, электронное сканирование луча",
        "метеорологические и навигационные РЛС: отличия задач",
        "СВЧ-диапазоны для локации: поглощение, дождь, зона обзора",
        "пассивная локация и бистатические схемы (идея)",
        "маркировка целей: IFF, ответчики, коды (общие принципы)",
        "подавление боковых лепестков и УБЛ (идея, без расчётов оружия)",
        "РЛС на БПЛА и авиации: ограничения по массе и энергии",
        "радиолокационные изображения: SAR, разрешение (обзорно)",
        "история: магнетрон, ранние РЛС Второй мировой (факты)",
        "безопасность: облучение, нормы для гражданских радаров (общие сведения)",
        "только учебный контент: без ТТХ секретных систем и без инструкций по обходу ПВО",
    ],
    "flight_controllers": [
        "роль полётного контроллера: сенсоры → оценка состояния → команды на исполнительные органы",
        "IMU: гироскопы, акселерометры, магнитометр — что измеряют и какие ошибки типичны",
        "сведение данных: комплементарный фильтр, Kalman (идея, без вывода формул в ответе)",
        "контуры PID: rate vs angle, настройка P/I/D на интуитивном уровне",
        "режимы полёта: стабилизация, удержание высоты, удержание позиции, RTH (принципы)",
        "PWM, OneShot, DShot — зачем нужны цифровые протоколы к регуляторам",
        "ESC: частота, направление вращения, синхронизация с мотором",
        "барометр и удержание высоты: дрейф, вентиляция корпуса",
        "GPS/ГНСС: точность, частота обновления, RTK (обзорно)",
        "арминг, failsafe: потеря сигнала, низкий заряд, поведение по умолчанию",
        "вибрации и шум гироскопа: фильтрация, демпфирование рамы",
        "калибровка: аксель, магнит, уровень горизонта",
        "избыточность сенсоров и отказоустойчивость (идея)",
        "прошивки и стеки: общие отличия open-source стеков (без пошаговых хаков)",
        "безопасность: пропеллеры, ток, ЛСП — только общие правила, без модификаций под вред",
        "только образовательный контент: без обхода ограничителей и закона",
    ],
    "aerodynamics": [
        "подъёмная сила: угол атаки, обводы профиля, обрыв потока (учебный уровень)",
        "профиль крыла: кривизна, угол установки, центр давления vs центр масс",
        "индуктивное и профильное сопротивление, поляра крыла (идеи)",
        "число Рейнольдса и режимы обтекания: ламинарный и турбулентный пограничный слой",
        "скольжение: соотношение крена и скольжения, крутой вираж",
        "стабильность: продольная, боковая, диэдр крыла, запилёность",
        "винт/пропеллер: шаг, диаметр, КПД, вихревое кольцо (обзорно)",
        "вертолётный несущий винт: циклический шаг, соосная схема vs классика (принципы)",
        "сжимаемость: число Маха, критическое М, звуковой барьер (общие факты)",
        "спутник и космос: сопло, сверхзвук в сопле (учебно, без ТТХ ракет)",
        "вихри на крыле: закон Кутты–Жуковского на уровне «что означает»",
        "поток в трубе и вокруг тела: торможение, разрежение",
        "авиационные единицы: узлы, футы в минуту, перевод в СИ (задачи)",
        "безопасность испытаний моделей: только общие принципы",
        "только учебная аэродинамика: без расчётов оружия и без данных закрытых проектов",
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
    """Промпт генерации MCQ по выбранной теме и грейду."""
    topic_key = (topic or "").strip().lower()
    if topic_key not in _ALLOWED_TOPICS:
        topic_key = "python"

    # Выбираем один конкретный аспект на стороне Python — так промпт остаётся коротким
    # и модели не нужно самой принимать решение о разнообразии
    aspect = random.choice(_TOPIC_ASPECTS[topic_key])
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

    edu_safety = ""
    if topic_key in (
        "uavs",
        "military_tactics",
        "reb",
        "lrs",
        "flight_controllers",
        "aerodynamics",
    ):
        edu_safety = (
            "- Educational, neutral content only (theory, history, regulations, technology). "
            "No instructions for harm, no extremism, no facilitation of illegal activity.\n"
        )

    avoid_block = ""
    if seen_questions:
        items = "\n".join(f"- {q}" for q in seen_questions)
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
        f"{edu_safety}"
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
        preview = raw[:_JSON_LOG_PREVIEW_LEN] + ("…" if len(raw) > _JSON_LOG_PREVIEW_LEN else "")
        logger.warning("Failed to parse quiz JSON (%s): %s", exc, preview)
        msg = "Invalid JSON from model"
        raise ValueError(msg) from exc

    return quiz_data_from_dict(data, default_grade=default_grade)


def quiz_data_from_dict(data: dict[str, Any], *, default_grade: str) -> QuizQuestionData:
    """Проверить структуру dict и собрать QuizQuestionData."""
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
