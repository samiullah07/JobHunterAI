"""Application filling use case — orchestrates form-fill and submit with HITL gate."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from jobhunter.adapters.browser.submitter import submit_application
from jobhunter.domain.application_fill import (
    ApprovalToken,
    ReviewPacket,
    SubmitResult,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

    from jobhunter.application.ports.form_filler import FormFiller

logger = structlog.get_logger()


class ApplicationFillingService:
    """Fill application forms and gate submission behind human approval."""

    def __init__(self, form_filler: FormFiller) -> None:
        self._form_filler = form_filler

    async def fill(
        self,
        url: str,
        field_plan: dict[str, str],
        files: dict[str, str],
        application_id: str,
        job_id: str,
        profile_id: str,
    ) -> ReviewPacket:
        """Fill the form and return a ReviewPacket. NEVER submits."""
        packet = await self._form_filler.fill(
            url=url,
            field_plan=field_plan,
            files=files,
            application_id=application_id,
            job_id=job_id,
            profile_id=profile_id,
        )
        logger.info(
            "application_filled",
            application_id=application_id,
            ready=packet.is_ready_for_review,
            blocker_count=len(packet.blockers),
        )
        return packet

    async def submit(
        self,
        page: Page,
        packet: ReviewPacket,
        approval: ApprovalToken,
    ) -> SubmitResult:
        """Submit — delegates to the guarded submit_application function."""
        result = await submit_application(page, packet, approval)
        logger.info(
            "application_submit_result",
            application_id=packet.application_id,
            submitted=result.submitted,
            error=result.error,
        )
        return result
