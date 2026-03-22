"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

from src.core.config import Settings
from src.infrastructure.ai.factory import build_provider_registry
from src.infrastructure.ai.routing_provider import RoutingAIProvider
from src.infrastructure.db.session import create_engine, create_session_factory
from src.infrastructure.logging_config import configure_loguru
from src.infrastructure.redis.client import create_redis_client
from src.interfaces.api.routes import admin, health, quiz, submissions, tasks, users

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application with wiring and middleware."""
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_loguru(level=settings.log_level, app_env=settings.app_env)
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        redis = create_redis_client(str(settings.redis_url))

        ollama_http: httpx.AsyncClient | None = None
        if settings.ollama_base_url is not None:
            ollama_http = httpx.AsyncClient(
                base_url=str(settings.ollama_base_url).rstrip("/"),
                timeout=httpx.Timeout(settings.ai_timeout),
            )

        openai_async: AsyncOpenAI | None = None
        if settings.yandex_folder_id and settings.yandex_auth:
            openai_async = AsyncOpenAI(
                api_key=settings.yandex_auth,
                base_url=str(settings.yandex_openai_base_url).rstrip("/"),
                project=settings.yandex_folder_id,
                timeout=float(settings.ai_timeout),
            )

        registry = build_provider_registry(
            settings,
            httpx_client=ollama_http,
            openai_client=openai_async,
        )
        ai_service = RoutingAIProvider(settings, redis, registry)

        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.redis = redis
        app.state.ollama_http = ollama_http
        app.state.openai_client = openai_async
        app.state.ai_service = ai_service

        logger.info("starting api (env=%s, ai_backend=%s)", settings.app_env, settings.ai_backend)
        yield
        if ollama_http is not None:
            await ollama_http.aclose()
        if openai_async is not None:
            await openai_async.close()
        await redis.aclose()  # type: ignore[attr-defined]
        await engine.dispose()
        logger.info("api shutdown complete")

    app = FastAPI(title="Code Quest", version="0.1.0", lifespan=lifespan)

    public_origin = str(settings.public_base_url).rstrip("/")
    origins = (
        ["*"]
        if settings.app_env == "development"
        else [public_origin, str(settings.webapp_url).rstrip("/")]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(submissions.router)
    app.include_router(tasks.router)
    app.include_router(users.router)
    app.include_router(admin.router)
    app.include_router(quiz.router)

    static_root = Path(__file__).resolve().parent.parent / "static"
    miniapp_root = static_root / "miniapp"
    admin_root = static_root / "admin"

    if miniapp_root.is_dir():
        app.mount(
            "/miniapp",
            StaticFiles(directory=str(miniapp_root), html=True),
            name="miniapp",
        )
    else:
        logger.warning("Mini App static dir missing: %s", miniapp_root)

    if admin_root.is_dir():
        app.mount(
            "/admin",
            StaticFiles(directory=str(admin_root), html=True),
            name="admin",
        )
    else:
        logger.warning("Admin static dir missing: %s", admin_root)

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        """Корень: веб-панель (управление/статистика). Mini App — /miniapp/."""
        return RedirectResponse(url="/admin/", status_code=307)

    return app
