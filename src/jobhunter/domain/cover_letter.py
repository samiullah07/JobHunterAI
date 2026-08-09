"""Domain DTOs for cover letter generation."""

from __future__ import annotations

from pydantic import BaseModel

from jobhunter.domain.resume import FabricationReport


class CoverLetter(BaseModel):
    """Structured cover letter — prose fields scannable by the fabrication validator."""

    salutation: str
    opening: str
    body_paragraphs: list[str]
    closing: str
    signature: str
    company_name: str
    role: str


class CoverLetterGenerationResult(BaseModel):
    cover_letter_version_id: str | None = None
    storage_keys: dict[str, str] = {}
    fabrication_report: FabricationReport = FabricationReport()
    fabrication_detected: bool = False
    below_threshold: bool = False
    no_score: bool = False
    reason: str | None = None
