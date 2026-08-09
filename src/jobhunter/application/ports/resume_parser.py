"""Resume parser port — interface for extracting structured profile data from files."""

from __future__ import annotations

from typing import Protocol

from jobhunter.domain.profile import ParsedResume


class ResumeParser(Protocol):
    async def parse(self, file_bytes: bytes, filename: str) -> ParsedResume: ...
