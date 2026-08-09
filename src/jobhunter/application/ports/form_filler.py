"""Form filler port — provider-agnostic interface for browser automation."""

from __future__ import annotations

from typing import Protocol

from jobhunter.domain.application_fill import ReviewPacket


class FormFiller(Protocol):
    async def fill(
        self,
        url: str,
        field_plan: dict[str, str],
        files: dict[str, str],
        application_id: str,
        job_id: str,
        profile_id: str,
    ) -> ReviewPacket: ...
