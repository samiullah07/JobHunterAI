"""Unit tests for the Groq LLM client — mocked AsyncOpenAI, no network."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from jobhunter.adapters.llm.groq_client import (
    GroqLlmClient,
    LlmBudgetExceeded,
    LlmParseError,
    UsageTracker,
)


def _make_mock_client(content: str) -> AsyncMock:
    """Create a mocked AsyncOpenAI that returns a canned chat completion."""
    mock_client = AsyncMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    mock_client.chat.completions.create = AsyncMock(return_value=response)
    return mock_client


class TestGroqLlmClient:
    async def test_parses_json_response(self) -> None:
        mock = _make_mock_client('{"skills": 0.9, "rationale": "good match"}')
        tracker = UsageTracker(daily_cap=100)
        client = GroqLlmClient(
            api_key="test-key",
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            usage_tracker=tracker,
            client=mock,
        )
        result = await client.complete_json("system", "user", "hint")
        assert result["skills"] == 0.9
        assert result["rationale"] == "good match"
        assert tracker.calls_today == 1

    async def test_daily_cap_raises_budget_exceeded(self) -> None:
        mock = _make_mock_client('{"ok": true}')
        tracker = UsageTracker(daily_cap=2)
        client = GroqLlmClient(
            api_key="test-key",
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            usage_tracker=tracker,
            client=mock,
        )
        await client.complete_json("s", "u", "h")
        await client.complete_json("s", "u", "h")
        with pytest.raises(LlmBudgetExceeded, match="Daily LLM call cap"):
            await client.complete_json("s", "u", "h")

    async def test_invalid_json_raises_parse_error(self) -> None:
        mock = _make_mock_client("not json at all")
        tracker = UsageTracker(daily_cap=100)
        client = GroqLlmClient(
            api_key="test-key",
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            usage_tracker=tracker,
            client=mock,
        )
        with pytest.raises(LlmParseError, match="Failed to parse"):
            await client.complete_json("s", "u", "h")

    def test_empty_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Groq API key is required"):
            GroqLlmClient(
                api_key="",
                base_url="https://api.groq.com/openai/v1",
                model="test",
                usage_tracker=UsageTracker(daily_cap=10),
            )


class TestUsageTracker:
    def test_check_passes_under_cap(self) -> None:
        tracker = UsageTracker(daily_cap=5)
        tracker.calls_today = 4
        tracker.check()

    def test_check_raises_at_cap(self) -> None:
        tracker = UsageTracker(daily_cap=5)
        tracker.calls_today = 5
        with pytest.raises(LlmBudgetExceeded):
            tracker.check()

    def test_record_call_increments(self) -> None:
        tracker = UsageTracker(daily_cap=10)
        tracker.record_call()
        tracker.record_call()
        assert tracker.calls_today == 2
