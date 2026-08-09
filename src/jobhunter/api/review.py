"""Review API — build review views, record human decisions.

SAFETY: POST /decision with APPROVE mints a token but NEVER submits.
The actual submit is a separate endpoint gated by the M8 ApprovalToken guard.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jobhunter.application.use_cases.review import ReviewService
from jobhunter.domain.review import (
    ApplicationReviewView,
    ReviewDecision,
    ReviewOutcome,
    ReviewRefused,
)
from jobhunter.infrastructure.db.session import get_session

router = APIRouter(prefix="/review", tags=["review"])


class DecisionRequest(BaseModel):
    decision: ReviewDecision
    approved_by: str | None = None
    note: str | None = None
    override: bool = False


def _get_review_service(session: Any = Depends(get_session)) -> ReviewService:  # noqa: B008
    return ReviewService(session)


@router.get("/applications/{application_id}", response_model=ApplicationReviewView)
async def get_review_view(
    application_id: str,
    service: ReviewService = Depends(_get_review_service),  # noqa: B008
) -> ApplicationReviewView:
    """Build the full review view for a human reviewer."""
    view = await service.build_review_view(application_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return view


@router.post("/applications/{application_id}/decision", response_model=ReviewOutcome)
async def record_decision(
    application_id: str,
    req: DecisionRequest,
    service: ReviewService = Depends(_get_review_service),  # noqa: B008
) -> ReviewOutcome:
    """Record a human review decision. APPROVE mints token — NEVER submits."""
    try:
        outcome = await service.record_decision(
            application_id=application_id,
            decision=req.decision,
            approved_by=req.approved_by,
            note=req.note,
            override=req.override,
        )
    except ReviewRefused as exc:
        raise HTTPException(status_code=409, detail=exc.reason) from exc
    return outcome
