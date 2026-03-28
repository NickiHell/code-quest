#!/usr/bin/env python3
"""Создать одну «задачу дня» на сегодня (UTC): удаляет прежние строки с тем же daily_for.

Запуск из корня репозитория (с настроенным .env):

    uv run python scripts/seed_daily_task.py
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete

from src.core.config import Settings
from src.infrastructure.db.models.task import TaskModel
from src.infrastructure.db.session import create_engine, create_session_factory


async def main() -> None:
    settings = Settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    today = datetime.now(tz=UTC).date()
    now = datetime.now(tz=UTC)

    async with factory() as session:
        await session.execute(delete(TaskModel).where(TaskModel.daily_for == today))
        session.add(
            TaskModel(
                title="Сумма двух чисел",
                description=(
                    "Напишите функцию add(a, b), возвращающую сумму a и b. "
                    "Учтите целые и отрицательные числа. Язык: Python 3."
                ),
                difficulty="easy",
                daily_for=today,
                created_at=now,
            ),
        )
        await session.commit()
    await engine.dispose()
    print(f"Seeded daily task for {today} (UTC).")


if __name__ == "__main__":
    asyncio.run(main())
