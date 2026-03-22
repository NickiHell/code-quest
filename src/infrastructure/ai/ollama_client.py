"""Low-level async client for Ollama HTTP API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """Thin wrapper around Ollama `/api/generate` (non-streaming)."""

    def __init__(self, client: httpx.AsyncClient, model: str) -> None:
        self._client = client
        self._model = model

    async def generate(self, prompt: str) -> str:
        """Return model text from a single generate call."""
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        response = await self._client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "")
        if not isinstance(text, str):
            logger.warning("Unexpected Ollama response shape: %s", data)
            return str(text)
        return text
