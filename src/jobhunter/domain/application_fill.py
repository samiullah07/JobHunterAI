"""Domain DTOs for application filling and human-in-the-loop submission."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FieldType(StrEnum):
    TEXT = "text"
    EMAIL = "email"
    TEL = "tel"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE = "date"
    FILE = "file"


class FilledField(BaseModel):
    selector: str
    label: str
    field_type: FieldType
    value: str
    source: str


class BlockerKind(StrEnum):
    CAPTCHA = "CAPTCHA"
    LOGIN_WALL = "LOGIN_WALL"
    UNMAPPED_REQUIRED_FIELD = "UNMAPPED_REQUIRED_FIELD"
    UPLOAD_FAILED = "UPLOAD_FAILED"


class Blocker(BaseModel):
    kind: BlockerKind
    detail: str


class ReviewPacket(BaseModel):
    application_id: str
    job_id: str
    profile_id: str
    url: str
    filled_fields: list[FilledField] = []
    uploaded_files: list[str] = []
    screenshots: list[str] = []
    blockers: list[Blocker] = []
    fill_hash: str = ""
    is_ready_for_review: bool = False

    def compute_fill_hash(self) -> str:
        content = json.dumps(
            {
                "application_id": self.application_id,
                "fields": [f.model_dump(mode="json") for f in self.filled_fields],
                "uploads": self.uploaded_files,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


class ApprovalToken(BaseModel):
    application_id: str
    fill_hash: str
    approved_by: str
    approved_at: datetime
    nonce: str = Field(default_factory=lambda: uuid.uuid4().hex)
    consumed: bool = False

    @classmethod
    def for_packet(cls, packet: ReviewPacket, approved_by: str) -> ApprovalToken:
        return cls(
            application_id=packet.application_id,
            fill_hash=packet.compute_fill_hash(),
            approved_by=approved_by,
            approved_at=datetime.now(),
        )


class SubmitResult(BaseModel):
    submitted: bool = False
    application_id: str = ""
    error: str | None = None


class SubmitNotAuthorized(Exception):
    """Raised when submit is attempted without a valid approval token."""
