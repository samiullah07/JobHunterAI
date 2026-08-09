"""Synchronous DB read/write path for the Streamlit review UI.

Streamlit runs inside an asyncio event loop, and the app is synchronous, so this
module deliberately uses ONLY sync SQLAlchemy and plain file I/O. No asyncio,
no await, no aiofiles, no async session — nothing that breaks under a running loop.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import String, create_engine, select, text
from sqlalchemy.orm import Session, selectinload
from jobhunter.config import get_settings
from jobhunter.infrastructure.db import models
from jobhunter.domain.enums import ApplicationStatus

def get_sync_url() -> str:
    """Convert the async DB URL to a sync (psycopg2) URL."""
    url = get_settings().database_url
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


_engine = create_engine(get_sync_url(), future=True)


def _read_text_file(key: str | None) -> str:
    """Read a stored text artifact by key/path, sync. Returns '' if missing."""
    if not key:
        return ""
    try:
        base = Path(get_settings().storage_local_dir)
        p = base / key
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return ""


def load_review_queue(limit: int = 50) -> list[dict[str, Any]]:
    """Return applications in READY_FOR_REVIEW status as simple dicts."""
    out: list[dict[str, Any]] = []
    with Session(_engine) as s:
        rows = s.execute(
            text(
                "SELECT id, job_id FROM applications "
                "WHERE status::text ILIKE 'ready_for_review' LIMIT :lim"
            ),
            {"lim": limit},
        ).all()
        for row in rows:
            app_id, job_id = row[0], row[1]
            job = s.get(models.Job, job_id) if job_id else None
            out.append(
                {
                    "id": str(app_id),
                    "company": getattr(job, "company_name", None) or "Unknown",
                    "role": getattr(job, "title", None) or "Unknown role",
                    "status": "ready_for_review",
                }
            )
    return out
def build_review_view_sync(application_id: str) -> dict[str, Any]:
    """Assemble everything the review screen needs, as a plain dict."""
    app_uuid = uuid.UUID(str(application_id))
    with Session(_engine) as s:
        app = s.get(models.Application, app_uuid)
        if app is None:
            raise ValueError(f"Application {application_id} not found")

        job = s.get(models.Job, app.job_id) if app.job_id else None
        resume = (
            s.get(models.ResumeVersion, app.resume_version_id)
            if getattr(app, "resume_version_id", None)
            else None
        )
        letter = (
            s.get(models.CoverLetterVersion, app.cover_letter_version_id)
            if getattr(app, "cover_letter_version_id", None)
            else None
        )

        # Résumé preview: prefer a markdown storage key, else canonical json text.
        resume_preview = ""
        if resume is not None:
            keys = getattr(resume, "storage_keys", None) or {}
            resume_preview = _read_text_file(keys.get("markdown")) if isinstance(keys, dict) else ""
            if not resume_preview:
                cj = getattr(resume, "canonical_json", None)
                resume_preview = str(cj) if cj else ""

        cover_letter_preview = getattr(letter, "body_markdown", "") or "" if letter else ""

        return {
            "id": str(app.id),
            "company": getattr(job, "company_name", None) or "Unknown",
            "role": getattr(job, "title", None) or "Unknown role",
            "location": getattr(job, "location", None) or "",
            "status": str(app.status),
            "resume_preview": resume_preview,
            "cover_letter_preview": cover_letter_preview,
            "filled_fields": [],       # populated from ReviewPacket if you store it
            "screenshots": [],         # populated from ReviewPacket screenshot keys
            "fabrication_reports": [],
            "blockers": [],
            "is_ready_for_review": True,
            "notes": getattr(app, "notes", "") or "",
        }


def record_decision_sync(
    application_id: str,
    decision: str,
    *,
    approved_by: str | None = None,
    note: str | None = None,
    override: bool = False,
) -> dict[str, Any]:
    """Record a human review decision. APPROVE sets status APPROVED. NEVER submits."""
    app_uuid = uuid.UUID(str(application_id))
    decision = decision.upper()

    status_map = {
            "APPROVE": ApplicationStatus.APPROVED,
            "REJECT": ApplicationStatus.REJECTED,
            "SKIP": ApplicationStatus.SKIPPED,
            "EDIT": ApplicationStatus.READY_FOR_REVIEW,
            "REGENERATE": ApplicationStatus.READY_FOR_REVIEW,
        }
    new_status = status_map.get(decision)
    if new_status is None:
        raise ValueError(f"Unknown decision: {decision}")

    with Session(_engine) as s:
        app = s.get(models.Application, app_uuid)
        if app is None:
            raise ValueError(f"Application {application_id} not found")
        app.status = new_status
        if note:
            existing = getattr(app, "notes", "") or ""
            app.notes = (existing + "\n" + note).strip()
        s.commit()

    # APPROVE mints a token but does NOT submit. Token binding to fill_hash lives in
    # the M8 ApprovalToken; wiring the real submit is a later, separate step.
    token = None
    if decision == "APPROVE":
        token = {"application_id": str(app_uuid), "approved_by": approved_by or "human", "submitted": False}

    return {
        "application_id": str(app_uuid),
        "decision": decision,
        "new_status": new_status,
        "approval_token": token,
        "submitted": False,
    }