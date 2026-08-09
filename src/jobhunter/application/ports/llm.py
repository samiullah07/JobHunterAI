"""LLM client port — provider-agnostic interface for structured JSON completion."""

from __future__ import annotations

from typing import Any, Protocol


class LlmClient(Protocol):
    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]: ...
