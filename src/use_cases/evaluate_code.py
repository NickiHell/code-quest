from __future__ import annotations

from src.core.interfaces.ai_provider import AbstractAIProvider


class EvaluateCodeUseCase:
    """Delegates code review to the configured AI backend."""

    def __init__(self, ai: AbstractAIProvider) -> None:
        self._ai = ai

    async def execute(self, code: str, task_description: str) -> str:
        """Return textual feedback from the model."""
        return await self._ai.evaluate_code(code, task_description)
