"""Domain DTOs for human-in-the-loop application review and decision recording."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from jobhunter.domain.application_fill import (
    ApprovalToken,
    Blocker,
    FilledField,
)
from jobhunter.domain.resume import FabricationReport


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    REGENERATE = "regenerate"
    SKIP = "skip"


class ApplicationReviewView(BaseModel):
    """Aggregate the UI renders — everything a human needs to decide in under a minute."""

    application_id: str
    job_id: str
    profile_id: str

    # Job summary
    company: str = ""
    role: str = ""
    location: str = ""
    salary: str = ""
    match_score: float | None = None
    match_rationale: str = ""

    # Artifacts
    resume_version_id: str | None = None
    resume_preview_markdown: str = ""
    cover_letter_version_id: str | None = None
    cover_letter_preview_markdown: str = ""

    # Application form state (from ReviewPacket)
    filled_fields: list[FilledField] = []
    uploaded_files: list[str] = []
    screenshot_keys: list[str] = []

    # Safety signals — shown prominently before approval controls
    fabrication_report_resume: FabricationReport | None = None
    fabrication_report_cover_letter: FabricationReport | None = None
    blockers: list[Blocker] = []
    is_ready_for_review: bool = False

    # Approval state
    approval_token: ApprovalToken | None = None

    @property
    def has_blocking_issues(self) -> bool:
        """True if there are blockers or fabrication violations that need attention."""
        has_blockers = len(self.blockers) > 0
        resume_dirty = (
            self.fabrication_report_resume is not None
            and not self.fabrication_report_resume.is_clean
        )
        letter_dirty = (
            self.fabrication_report_cover_letter is not None
            and not self.fabrication_report_cover_letter.is_clean
        )
        return has_blockers or resume_dirty or letter_dirty or not self.is_ready_for_review


class ReviewOutcome(BaseModel):
    """Result of a review decision — returned to the UI after a human acts."""

    application_id: str
    decision: ReviewDecision
    token: ApprovalToken | None = None
    note: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    override_used: bool = False
    refused: bool = False
    refusal_reason: str | None = None


class ReviewRefused(Exception):
    """Raised when APPROVE is attempted without override on a blocked application."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)
