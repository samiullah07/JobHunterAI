"""Application filling API router — fill and submit with HITL gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jobhunter.adapters.browser.playwright_form_filler import PlaywrightFormFiller
from jobhunter.adapters.storage.local_storage import LocalStorageService
from jobhunter.application.use_cases.application_filling import (
    ApplicationFillingService,
)
from jobhunter.config import get_settings
from jobhunter.domain.application_fill import (
    ApprovalToken,
    ReviewPacket,
    SubmitNotAuthorized,
)

router = APIRouter(prefix="/applications", tags=["applications"])


class FillRequest(BaseModel):
    url: str
    field_plan: dict[str, str]
    files: dict[str, str] = {}
    application_id: str
    job_id: str
    profile_id: str


class SubmitRequest(BaseModel):
    packet: ReviewPacket
    approval: ApprovalToken


def _get_filling_service() -> ApplicationFillingService:
    settings = get_settings()
    storage = LocalStorageService(settings.storage_local_dir)
    filler = PlaywrightFormFiller(storage, headless=settings.browser_headless)
    return ApplicationFillingService(form_filler=filler)


@router.post("/fill")
async def fill_application(
    req: FillRequest,
    service: ApplicationFillingService = Depends(_get_filling_service),  # noqa: B008
) -> ReviewPacket:
    """Fill a job application form — NEVER submits."""
    packet = await service.fill(
        url=req.url,
        field_plan=req.field_plan,
        files=req.files,
        application_id=req.application_id,
        job_id=req.job_id,
        profile_id=req.profile_id,
    )
    if packet.blockers:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Blockers detected — cannot proceed",
                "blockers": [b.model_dump() for b in packet.blockers],
                "packet": packet.model_dump(mode="json"),
            },
        )
    return packet


@router.post("/submit")
async def submit_application_endpoint(
    req: SubmitRequest,
) -> dict[str, object]:
    """Submit a previously filled application — requires valid ApprovalToken."""
    try:
        # Note: In production this would use the existing browser session.
        # For now, we validate the guard logic server-side and return the result.
        from jobhunter.adapters.browser.submitter import _verify_approval

        _verify_approval(req.packet, req.approval)
    except SubmitNotAuthorized as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {
        "message": "Approval verified — submit authorized",
        "application_id": req.packet.application_id,
    }
