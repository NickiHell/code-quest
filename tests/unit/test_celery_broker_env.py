from __future__ import annotations

import pytest

from src.core.config import celery_broker_url_from_environ


def test_celery_broker_url_prefers_celery_broker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://host:6379/9")
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert celery_broker_url_from_environ() == "redis://host:6379/9"


def test_celery_broker_url_derives_from_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    assert celery_broker_url_from_environ() == "redis://localhost:6379/1"


def test_celery_broker_url_requires_redis_or_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValueError, match="REDIS_URL"):
        celery_broker_url_from_environ()
