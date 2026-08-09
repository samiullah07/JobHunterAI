"""Groq LLM client — implements LlmClient port via OpenAI-compatible API."""

from __future__ import annotations

import json
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()


class LlmBudgetExceeded(Exception):
    """Raised when daily LLM call cap is reached."""


class LlmParseError(Exception):
    """Raised when LLM response is not valid JSON."""


class UsageTracker:
    """In-memory daily call counter for rate-limit guardrail."""

    def __init__(self, daily_cap: int) -> None:
        self.daily_cap = daily_cap
        self.calls_today: int = 0

    def check(self) -> None:
        if self.calls_today >= self.daily_cap:
            raise LlmBudgetExceeded(
                f"Daily LLM call cap reached: {self.calls_today}/{self.daily_cap}"
            )

    def record_call(self) -> None:
        self.calls_today += 1


class GroqLlmClient:
    """Implements LlmClient via Groq's OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        usage_tracker: UsageTracker,
        client: AsyncOpenAI | None = None,
    ) -> None:
        if not api_key:
            msg = "Groq API key is required (set GROQ_API_KEY)"
            raise ValueError(msg)
        self._model = model
        self._tracker = usage_tracker
        self._client = client or AsyncOpenAI(api_key=api_key, base_url=base_url)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=15),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        self._tracker.check()

        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        self._tracker.record_call()

        content = resp.choices[0].message.content or ""
        try:
            return json.loads(content)  # type: ignore[no-any-return]
        except (json.JSONDecodeError, TypeError) as exc:
            raise LlmParseError(f"Failed to parse LLM JSON: {content[:200]}") from exc
