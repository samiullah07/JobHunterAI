"""Review use case — builds the review view and records human decisions.

SAFETY: This module has NO dependency on submit_application or any browser submit path.
APPROVE mints an ApprovalToken and records the decision — it NEVER submits.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog

from jobhunter.domain.application_fill import ApprovalToken, ReviewPacket
from jobhunter.domain.enums import ApplicationStatus
from jobhunter.domain.resume import FabricationReport
from jobhunter.domain.review import (
    ApplicationReviewView,
    ReviewDecision,
    ReviewOutcome,
    ReviewRefused,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.infrastructure.db.models import Application

logger = structlog.get_logger()


class ReviewService:
    """Orchestrates the review view assembly and decision recording.

    This service intentionally has NO dependency on submitter.py or any submit
    path. The APPROVE action mints a token and persists the decision — the
    actual submission is a separate, later step gated by the M8 guard.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_review_view(self, application_id: str) -> ApplicationReviewView | None:
        """Assemble everything the human needs to decide in under a minute."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from jobhunter.infrastructure.db.models import (
            Application,
            CoverLetterVersion,
            MatchScore,
            ResumeVersion,
        )

        app_uuid = uuid.UUID(application_id)
        stmt = (
            select(Application)
            .where(Application.id == app_uuid)
            .options(
                selectinload(Application.job),
                selectinload(Application.answers),
                selectinload(Application.screenshots),
            )
        )
        result = await self._session.execute(stmt)
        app: Application | None = result.scalar_one_or_none()
        if app is None:
            return None

        job = app.job

        # Match score
        score_stmt = (
            select(MatchScore)
            .where(
                MatchScore.job_id == app.job_id,
                MatchScore.profile_id == app.profile_id,
            )
            .order_by(MatchScore.created_at.desc())
            .limit(1)
        )
        score_result = await self._session.execute(score_stmt)
        match_score_row = score_result.scalars().first()

        # Resume version
        resume_markdown = ""
        resume_version_id: str | None = None
        fabrication_resume: FabricationReport | None = None
        if app.resume_version_id:
            rv_stmt = select(ResumeVersion).where(ResumeVersion.id == app.resume_version_id)
            rv_result = await self._session.execute(rv_stmt)
            rv = rv_result.scalar_one_or_none()
            if rv:
                resume_version_id = str(rv.id)
                if rv.canonical_json:
                    resume_markdown = _render_resume_markdown(rv.canonical_json)
                if rv.canonical_json and rv.canonical_json.get("fabrication_report"):
                    fabrication_resume = FabricationReport(
                        **rv.canonical_json["fabrication_report"]
                    )

        # Cover letter version
        cover_markdown = ""
        cover_version_id: str | None = None
        fabrication_cover: FabricationReport | None = None
        if app.cover_letter_version_id:
            cl_stmt = select(CoverLetterVersion).where(
                CoverLetterVersion.id == app.cover_letter_version_id
            )
            cl_result = await self._session.execute(cl_stmt)
            cl = cl_result.scalar_one_or_none()
            if cl:
                cover_version_id = str(cl.id)
                cover_markdown = cl.body_markdown or ""

        # Build ReviewPacket from application answers/screenshots
        review_packet = _build_review_packet_from_app(app)

        # Salary display
        salary = ""
        if job.salary_min or job.salary_max:
            currency = job.salary_currency or "USD"
            parts = []
            if job.salary_min:
                parts.append(f"{currency} {job.salary_min:,.0f}")
            if job.salary_max:
                parts.append(f"{currency} {job.salary_max:,.0f}")
            salary = " – ".join(parts)

        return ApplicationReviewView(
            application_id=str(app.id),
            job_id=str(app.job_id),
            profile_id=str(app.profile_id),
            company=job.company_name,
            role=job.title,
            location=job.location or "",
            salary=salary,
            match_score=match_score_row.overall if match_score_row else None,
            match_rationale=match_score_row.rationale or "" if match_score_row else "",
            resume_version_id=resume_version_id,
            resume_preview_markdown=resume_markdown,
            cover_letter_version_id=cover_version_id,
            cover_letter_preview_markdown=cover_markdown,
            filled_fields=review_packet.filled_fields,
            uploaded_files=review_packet.uploaded_files,
            screenshot_keys=review_packet.screenshots,
            fabrication_report_resume=fabrication_resume,
            fabrication_report_cover_letter=fabrication_cover,
            blockers=review_packet.blockers,
            is_ready_for_review=review_packet.is_ready_for_review,
        )

    async def record_decision(
        self,
        application_id: str,
        decision: ReviewDecision,
        *,
        approved_by: str | None = None,
        note: str | None = None,
        override: bool = False,
    ) -> ReviewOutcome:
        """Record a human review decision.

        APPROVE mints a token and persists the decision — it NEVER calls submit_application — that is a separate step.
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from jobhunter.infrastructure.db.models import Application

        app_uuid = uuid.UUID(application_id)
        stmt = select(Application).where(Application.id == app_uuid).options(
            selectinload(Application.job),
            selectinload(Application.answers),
            selectinload(Application.screenshots),
        )
        result = await self._session.execute(stmt)
        app: Application | None = result.scalar_one_or_none()
        if app is None:
            return ReviewOutcome(
                application_id=application_id,
                decision=decision,
                refused=True,
                refusal_reason="Application not found",
            )

        review_packet = _build_review_packet_from_app(app)

        if decision == ReviewDecision.APPROVE:
            return await self._handle_approve(
                app, review_packet, approved_by=approved_by, note=note, override=override
            )
        elif decision == ReviewDecision.REJECT:
            return await self._handle_reject(app, note=note)
        elif decision == ReviewDecision.SKIP:
            return await self._handle_skip(app, note=note)
        else:
            # EDIT / REGENERATE — record intent
            return await self._handle_rework(app, decision, note=note)

    async def _handle_approve(
        self,
        app: Application,
        packet: ReviewPacket,
        *,
        approved_by: str | None,
        note: str | None,
        override: bool,
    ) -> ReviewOutcome:
        """Mint token, update status. NEVER submit."""
        # Safety gate: require override if there are blocking issues
        has_blockers = len(packet.blockers) > 0 or not packet.is_ready_for_review
        if has_blockers and not override:
            logger.warning(
                "approve_refused_blockers",
                application_id=str(app.id),
                blocker_count=len(packet.blockers),
            )
            raise ReviewRefused(
                "Cannot approve: blockers present or application not ready. "
                "Use override=True to force approval."
            )

        # SAFETY BOUNDARY: Mint token only. NO submit_application call.
        # The token is returned to the UI/caller. A separate, later step
        # passes it to submit_application (with the M8 guard).
        from jobhunter.infrastructure.db.models import ApprovalToken as ApprovalTokenORM

        token = ApprovalToken.for_packet(packet, approved_by=approved_by or "human")
        orm_token = ApprovalTokenORM(
            application_id=app.id,
            approval_hash=token.fill_hash,
            is_used=False,
        )
        self._session.add(orm_token)
        app.status = ApplicationStatus.APPROVED

        override_note = " [OVERRIDE: blockers present]" if override and has_blockers else ""
        app.notes = (app.notes or "") + f"\nApproved by {approved_by or 'human'}.{override_note}"
        if note:
            app.notes += f" Note: {note}"

        await self._session.flush()

        logger.info(
            "review_approved",
            application_id=str(app.id),
            approved_by=approved_by,
            override=override,
            fill_hash=token.fill_hash,
        )

        return ReviewOutcome(
            application_id=str(app.id),
            decision=ReviewDecision.APPROVE,
            token=token,
            note=note,
            override_used=override and has_blockers,
        )

    async def _handle_reject(self, app: Application, *, note: str | None) -> ReviewOutcome:
        app.status = ApplicationStatus.REJECTED
        app.notes = (app.notes or "") + f"\nRejected.{f' Note: {note}' if note else ''}"
        await self._session.flush()
        logger.info("review_rejected", application_id=str(app.id))
        return ReviewOutcome(application_id=str(app.id), decision=ReviewDecision.REJECT, note=note)

    async def _handle_skip(self, app: Application, *, note: str | None) -> ReviewOutcome:
        app.status = ApplicationStatus.SKIPPED
        app.notes = (app.notes or "") + f"\nSkipped.{f' Note: {note}' if note else ''}"
        await self._session.flush()
        logger.info("review_skipped", application_id=str(app.id))
        return ReviewOutcome(application_id=str(app.id), decision=ReviewDecision.SKIP, note=note)

    async def _handle_rework(
        self, app: Application, decision: ReviewDecision, *, note: str | None
    ) -> ReviewOutcome:
        app.status = ApplicationStatus.READY_FOR_REVIEW
        action = "edit" if decision == ReviewDecision.EDIT else "regenerate"
        app.notes = (app.notes or "") + f"\nRequested {action}.{f' Note: {note}' if note else ''}"
        await self._session.flush()
        logger.info(f"review_{action}_requested", application_id=str(app.id))
        return ReviewOutcome(application_id=str(app.id), decision=decision, note=note)


def _build_review_packet_from_app(app: Application) -> ReviewPacket:
    """Construct a ReviewPacket from the Application ORM model's answers/screenshots."""
    from jobhunter.domain.application_fill import FieldType, FilledField

    filled_fields = []
    for ans in getattr(app, "answers", []):
        filled_fields.append(
            FilledField(
                selector=f"[question='{ans.question}']",
                label=ans.question or "",
                field_type=FieldType.TEXT,
                value=ans.value or "",
                source=ans.source or "unknown",
            )
        )

    screenshots = [s.storage_key for s in getattr(app, "screenshots", []) if s.storage_key]
    uploaded_files: list[str] = []

    packet = ReviewPacket(
        application_id=str(app.id),
        job_id=str(app.job_id),
        profile_id=str(app.profile_id),
        url="",
        filled_fields=filled_fields,
        uploaded_files=uploaded_files,
        screenshots=screenshots,
        blockers=[],
        is_ready_for_review=app.status == ApplicationStatus.READY_FOR_REVIEW,
    )
    packet.fill_hash = packet.compute_fill_hash()
    return packet


def _render_resume_markdown(canonical_json: dict) -> str:  # type: ignore[type-arg]
    """Render a minimal markdown preview from the stored canonical resume JSON."""
    lines: list[str] = []
    if "contact" in canonical_json:
        c = canonical_json["contact"]
        lines.append(f"# {c.get('name', 'Candidate')}")
        if c.get("email"):
            lines.append(f"**Email:** {c['email']}")
    if "summary" in canonical_json:
        lines.append(f"\n## Summary\n{canonical_json['summary']}")
    for exp in canonical_json.get("experience", []):
        lines.append(f"\n### {exp.get('title', '')} @ {exp.get('company', '')}")
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
    for edu in canonical_json.get("education", []):
        lines.append(f"\n**{edu.get('degree', '')}** — {edu.get('institution', '')}")
    if "skills" in canonical_json:
        skills = canonical_json["skills"]
        if isinstance(skills, list):
            for item in skills:
                if isinstance(item, dict):
                    cat = item.get('category') or 'Skills'
                    skill_list = item.get('skills', [])
                    lines.append('**' + str(cat) + ':** ' + ', '.join(str(s) for s in skill_list))
                elif isinstance(item, str):
                    lines.append('- ' + item)
        elif isinstance(skills, dict):
            for cat, items in skills.items():
                if isinstance(items, list):
                    lines.append(f"**{cat}:** {', '.join(items)}")
    return "\n".join(lines)