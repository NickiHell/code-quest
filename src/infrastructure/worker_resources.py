from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from openai import AsyncOpenAI
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.config import Settings
from src.infrastructure.ai.factory import build_provider_registry
from src.infrastructure.ai.routing_provider import RoutingAIProvider
from src.infrastructure.db.session import create_engine, create_session_factory
from src.infrastructure.redis.client import create_redis_client

WorkerStack = tuple[
    AsyncEngine,
    async_sessionmaker[AsyncSession],
    Redis,  # type: ignore[type-arg]
    RoutingAIProvider,
    AsyncOpenAI | None,
]


@asynccontextmanager
async def worker_stack(settings: Settings) -> AsyncIterator[WorkerStack]:
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    redis = create_redis_client(str(settings.redis_url))

    yandex_client: AsyncOpenAI | None = None
    if settings.yandex_folder_id and settings.yandex_auth:
        yandex_client = AsyncOpenAI(
            api_key=settings.yandex_auth,
            base_url=str(settings.yandex_openai_base_url).rstrip("/"),
            project=settings.yandex_folder_id,
            timeout=float(settings.ai_timeout),
        )

    registry = build_provider_registry(
        settings,
        yandex_client=yandex_client,
    )
    ai_service = RoutingAIProvider(settings, redis, registry)

    try:
        yield engine, session_factory, redis, ai_service, yandex_client
    finally:
        if yandex_client is not None:
            await yandex_client.close()
        await redis.aclose()  # type: ignore[attr-defined]
        await engine.dispose()
