from __future__ import annotations

from src.core.ai_backend import AiBackend
from src.core.config import Settings, migration_database_url


def test_migration_database_url_prefers_direct() -> None:
    s = Settings(
        secret_key="x" * 16,
        database_url="postgresql+asyncpg://u:p@pgbouncer:5432/db",
        database_url_direct="postgresql+asyncpg://u:p@postgres:5432/db",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        ai_backend=AiBackend.yandex_gpt,
        yandex_folder_id="f",
        yandex_auth="k",
    )
    assert "postgres" in migration_database_url(s)
    assert "pgbouncer" not in migration_database_url(s)


def test_migration_database_url_falls_back_to_runtime() -> None:
    s = Settings(
        secret_key="x" * 16,
        database_url="postgresql+asyncpg://u:p@db:5432/db",
        redis_url="redis://localhost:6379/0",
        bot_token="1234567890:ABCDEF-test",
        webapp_url="https://example.com/m/",
        public_base_url="https://example.com",
        telegram_webhook_secret="0123456789abcdef",
        ai_backend=AiBackend.yandex_gpt,
        yandex_folder_id="f",
        yandex_auth="k",
    )
    assert migration_database_url(s) == str(s.database_url)
