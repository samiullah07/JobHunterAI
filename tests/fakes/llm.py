"""Fake LLM client for deterministic testing — no network, no API keys."""

from __future__ import annotations

from typing import Any


class FakeStructuringLLM:
    """Returns a deterministic ParsedResume-shaped dict from known input."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self._response = response

    async def complete_json(self, system: str, user: str, schema_hint: str) -> dict[str, Any]:
        if self._response is not None:
            return self._response
        return {
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+1-555-0100",
            "location": "San Francisco, CA",
            "headline": "Senior Software Engineer",
            "summary": "10 years building distributed systems.",
            "github_url": "https://github.com/janedoe",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "confidence": {
                "full_name": 0.99,
                "email": 0.95,
                "headline": 0.9,
                "summary": 0.85,
            },
            "work_experiences": [
                {
                    "company_name": "Acme Corp",
                    "title": "Senior Engineer",
                    "start_date": "2020-01-15",
                    "end_date": None,
                    "is_current": True,
                    "description": "Led backend team.",
                    "achievements": ["Reduced latency by 40%"],
                    "technologies": ["Python", "PostgreSQL"],
                }
            ],
            "skills": [
                {"name": "Python", "category": "Language", "proficiency": "Expert"},
                {"name": "PostgreSQL", "category": "Database", "proficiency": "Advanced"},
            ],
        }
