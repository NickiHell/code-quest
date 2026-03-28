from __future__ import annotations

import asyncio
import logging

from src.core.config import Settings

logger = logging.getLogger(__name__)


class DockerSandboxRunner:
    """Runs user code inside a disposable container (skeleton)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run_python_snippet(self, code: str) -> str:
        """Execute a Python snippet in an isolated container (placeholder)."""
        return await asyncio.to_thread(self._run_sync, code)

    def _run_sync(self, code: str) -> str:
        """Blocking sandbox path — extend with real image + resource limits."""
        import docker

        client = docker.from_env()
        try:
            logger.info(
                "Sandbox stub: would run code with timeout=%ss memory=%s network_disabled=%s",
                self._settings.sandbox_timeout,
                self._settings.sandbox_memory_limit,
                self._settings.sandbox_network_disabled,
            )
            _ = code
            return "sandbox-not-implemented"
        finally:
            client.close()
