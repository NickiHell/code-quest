# Code Quest

[![CI](https://github.com/NickiHell/code-quest/actions/workflows/ci.yml/badge.svg)](https://github.com/NickiHell/code-quest/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

Telegram-бот и **Mini App** с MCQ-квизом (обычно **5 вариантов** ответа на вопрос), общим **лидербордом** в Redis, API на **FastAPI** и генерацией текста через **Yandex Cloud** (YandexGPT, AI Studio, Responses API). Веб-админка для статистики.

**Архитектура:** слой **use cases** отделяет сценарии (квиз, сабмиты кода) от **инфраструктуры** (SQLAlchemy, Redis, HTTP-клиенты к LLM). Контракты в `core/interfaces/`; FastAPI собирает зависимости в `deps.py`. Для портфолио: один репозиторий — бот, Mini App, REST и админка с переключением бэкенда ИИ без перезапуска.

## Возможности

- Квиз по выбранной сложности (лёгкий / средний / эксперт), генерация вопросов через AI.
- Учёт очков и топ игроков.
- Telegram: команды, inline-кнопки; в **личке** Mini App через `web_app`; в **группах** кнопка ведёт на `t.me/<бот>?startapp`, чтобы открыть приложение **внутри Telegram**, а не во внешнем браузере.
- REST API, статика Mini App и админки, Docker Compose для локального запуска.

## Стек

Python 3.11+, FastAPI, SQLAlchemy (async) + PostgreSQL, Redis, Aiogram 3, Alembic, uv.

## Режимы ИИ и админка

В [.env.example](.env.example) — переменные **Yandex Cloud** (folder, ключ, модель). В рантайме можно переключать режим (`yandex_openai_responses`, `yandex_gpt`, `yandex_ai_studio_agent`) через админку или Redis, если для режима заданы креды.

- Значение по умолчанию: `AI_BACKEND`.
- Переключение **без перезапуска**: веб-админка `/admin/` (раздел «Режим ИИ») или
  `GET`/`PUT /api/admin/ai-backend` с заголовком `X-Admin-Key` (override хранится в Redis).

## Быстрый старт

1. Скопируйте [.env.example](.env.example) в `.env` и задайте минимум:

   - `BOT_TOKEN` — токен бота от [@BotFather](https://t.me/BotFather)
   - `WEBAPP_URL` — полный HTTPS-URL страницы Mini App (например `https://ваш-домен/miniapp/`)
   - `PUBLIC_BASE_URL` — тот же хост без пути (для `/admin/` и CORS)
   - `ADMIN_API_KEY` — не короче 16 символов

2. Запуск сервисов:

   ```bash
   docker compose up --build
   ```

3. Примените миграции БД (при необходимости из контейнера API или с хоста при установленных зависимостях):

   ```bash
   alembic upgrade head
   ```

API по умолчанию слушает порт `8000`, Mini App: `/miniapp/`, админка: `/` и `/admin/`.

## Mini App через ngrok (локально)

Telegram принимает только **HTTPS** для Web App. Для теста с машины без своего домена удобен [ngrok](https://ngrok.com/) (или аналог: Cloudflare Tunnel, localtunnel).

1. Поднимите стек: `docker compose up --build` (API на хосте: `http://127.0.0.1:8000`).
2. В другом терминале: `ngrok http 8000` и скопируйте выданный **https://…** URL (например `https://abcd-12-34-56.ngrok-free.app`).
3. В `.env` выставьте тот же хост:
   - `PUBLIC_BASE_URL=https://abcd-12-34-56.ngrok-free.app`
   - `WEBAPP_URL=https://abcd-12-34-56.ngrok-free.app/miniapp/` (со слэшем в конце пути по желанию, главное — рабочий URL страницы).
4. Перезапустите контейнеры (`docker compose up -d`), чтобы подтянуть переменные.
5. В [@BotFather](https://t.me/BotFather): для бота задайте домен Mini App / кнопку меню с тем же **https**-корнем, что и `PUBLIC_BASE_URL` (или прямой URL на `/miniapp/`).
6. Откройте бота в Telegram и запустите Mini App из кнопки.

**Замечания:** бесплатный ngrok меняет поддомен при перезапуске — обновляйте `.env` и BotFather. Страница-предупреждение ngrok в браузере на мобильном Telegram обычно не мешает открытию внутри клиента; если Mini App не грузится, проверьте CORS: в `development` у приложения часто разрешён `*`, иначе нужен ваш ngrok-оригин в настройках.

## Разработка без Docker

```bash
uv sync --group dev
npm ci
npm run lint
uv run pre-commit install
uv run ruff check .
uv run mypy src
uv run pytest
```

**Pre-commit** (после `pre-commit install`): перед коммитом запускаются проверки из [`.pre-commit-config.yaml`](.pre-commit-config.yaml) — правки YAML/TOML, trailing whitespace, ESLint для `static/**/*.js` (сложность, вложенность, `eqeqeq`, без `var`), `ruff check` с расширенным набором правил (см. `[tool.ruff.lint]` в `pyproject.toml`) и `ruff format`.
**Conventional Commits:** хук `commit-msg` проверяет заголовок сообщения (например `feat(scope): описание`). Удобно оформлять коммиты через [Commitizen](https://commitizen-tools.github.io/commitizen/): `uv run cz commit`.

Подробности переменных окружения — в [.env.example](.env.example).

## CI

Автоматические проверки: pre-commit (ESLint, Ruff), Mypy, Pytest. Статус и логи: [GitHub Actions](https://github.com/NickiHell/code-quest/actions).
