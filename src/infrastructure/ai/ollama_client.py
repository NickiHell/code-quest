"""Low-level async client for Ollama HTTP API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.core.exceptions import ExternalServiceError

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
        try:
            response = await self._client.post("/api/generate", json=payload)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ExternalServiceError(
                "Нет соединения с Ollama. Если API в Docker, на хосте задайте "
                "OLLAMA_HOST=0.0.0.0:11434 и в .env OLLAMA_BASE_URL=http://host.docker.internal:11434."
            ) from exc
        except httpx.TimeoutException as exc:
            raise ExternalServiceError("Таймаут запроса к Ollama.") from exc
        except httpx.HTTPStatusError as exc:
            raise ExternalServiceError(
                f"Ollama вернула ошибку HTTP {exc.response.status_code}."
            ) from exc
        data = response.json()
        text = data.get("response", "")
        if not isinstance(text, str):
            logger.warning("Unexpected Ollama response shape: %s", data)
            return str(text)
        return text
