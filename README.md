# Code Quest

[![CI](https://github.com/NickiHell/code-quest/actions/workflows/ci.yml/badge.svg)](https://github.com/NickiHell/code-quest/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

Telegram-бот и **Mini App** с MCQ-квизом (10 вариантов ответа), общим **лидербордом** в Redis, API на **FastAPI** и подключаемыми **AI-бэкендами** (Ollama, Yandex и др.). Веб-админка для статистики.

## Возможности

- Квиз по выбранному грейду (junior / middle / senior), генерация вопросов через AI.
- Учёт очков и топ игроков.
- Telegram: команды, inline-кнопки; в **личке** Mini App через `web_app`; в **группах** кнопка ведёт на `t.me/<бот>?startapp`, чтобы открыть приложение **внутри Telegram**, а не во внешнем браузере.
- REST API, статика Mini App и админки, Docker Compose для локального запуска.

## Стек

Python 3.11+, FastAPI, SQLAlchemy (async) + PostgreSQL, Redis, Aiogram 3, Alembic, uv.

## Режимы ИИ и админка

В [.env.example](.env.example) перечислены переменные для **Ollama**, **YandexGPT**, **ассистента AI Studio** и **Yandex OpenAI-compatible Responses**. Можно задать креды сразу для нескольких бэкендов: поднимутся все, для которых хватает переменных.

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
uv run pre-commit install
uv run ruff check .
uv run mypy src
uv run pytest
```

**Pre-commit** (после `pre-commit install`): перед коммитом запускаются проверки из [`.pre-commit-config.yaml`](.pre-commit-config.yaml) — правки YAML/TOML, trailing whitespace, `ruff check` и `ruff format`.
**Conventional Commits:** хук `commit-msg` проверяет заголовок сообщения (например `feat(scope): описание`). Удобно оформлять коммиты через [Commitizen](https://commitizen-tools.github.io/commitizen/): `uv run cz commit`.

Подробности переменных окружения — в [.env.example](.env.example).

## CI

Автоматические проверки: pre-commit (в т.ч. Ruff), Mypy, Pytest. Статус и логи: [GitHub Actions](https://github.com/NickiHell/code-quest/actions).
