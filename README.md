# code-quest

[![CI](https://github.com/NickiHell/code-quest/actions/workflows/ci.yml/badge.svg)](https://github.com/NickiHell/code-quest/actions/workflows/ci.yml)

**Стек:** Python 3.14+, FastAPI, SQLAlchemy 2 async, PostgreSQL, Redis, Aiogram 3, Alembic, uv.

**Структура:** `src/core` — домен и интерфейсы, `src/use_cases` — сценарии, `src/infrastructure` — БД/Redis/LLM, `src/interfaces` — HTTP и бот. Статика Mini App: `static/miniapp/`.

**Запуск:** `.env` из `.env.example`, затем `docker compose up --build`. API: `:8000`, Mini App: `/miniapp/`, `GET /api/health`.

**Переменные:** `SECRET_KEY`, `DATABASE_URL` (`postgresql+asyncpg://` или `sqlite+aiosqlite://`), `REDIS_URL`, `BOT_TOKEN`, `WEBAPP_URL`, `PUBLIC_BASE_URL`, параметры Yandex по `AI_BACKEND` (см. `.env.example`).

**Миграции:** `alembic upgrade head`. Сид задачи дня: `uv run python scripts/seed_daily_task.py`.

**Prod-compose:** `docker compose -f docker-compose.prod.yml up --build -d`.

**Локальная разработка:** `uv sync --group dev`, `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q --cov=src --cov-fail-under=90`.
