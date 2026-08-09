"""Application submitter — the ONLY place that clicks a submit control.

Requires a valid ApprovalToken that passes the guard before any click.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from jobhunter.domain.application_fill import (
    ApprovalToken,
    ReviewPacket,
    SubmitNotAuthorized,
    SubmitResult,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = structlog.get_logger()


def _verify_approval(packet: ReviewPacket, approval: ApprovalToken | None) -> ApprovalToken:
    """Guard: raises SubmitNotAuthorized unless the token is valid.

    Returns the validated (non-None) token so callers have a narrowed type
    without relying on bare asserts (which python -O strips).

    Checks:
    1. Token is present (not None).
    2. application_id matches the packet.
    3. fill_hash matches the CURRENT packet hash (ensures packet wasn't modified).
    4. Token is not already consumed.
    """
    if approval is None:
        logger.warning("submit_rejected", reason="no_token")
        raise SubmitNotAuthorized("No approval token provided")

    if approval.application_id != packet.application_id:
        logger.warning(
            "submit_rejected",
            reason="application_id_mismatch",
            token_app_id=approval.application_id,
            packet_app_id=packet.application_id,
        )
        raise SubmitNotAuthorized(
            f"Token application_id '{approval.application_id}' "
            f"does not match packet '{packet.application_id}'"
        )

    current_hash = packet.compute_fill_hash()
    if approval.fill_hash != current_hash:
        logger.warning(
            "submit_rejected",
            reason="hash_mismatch",
            token_hash=approval.fill_hash,
            current_hash=current_hash,
        )
        raise SubmitNotAuthorized(
            "Approval token hash does not match current packet — "
            "the form contents may have changed since approval"
        )

    if approval.consumed:
        logger.warning("submit_rejected", reason="token_consumed")
        raise SubmitNotAuthorized("Approval token has already been consumed")

    logger.info(
        "submit_approved",
        application_id=approval.application_id,
        approved_by=approval.approved_by,
    )
    return approval


async def submit_application(
    page: Page,
    packet: ReviewPacket,
    approval: ApprovalToken | None,
) -> SubmitResult:
    """Submit the application — ONLY after the guard passes.

    This is the ONLY function in the codebase that clicks submit.
    """
    validated = _verify_approval(packet, approval)

    # Guard passed — locate and click the submit control
    submit_btn = page.locator(
        "button[type='submit'], input[type='submit'], "
        "button:has-text('Submit'), button:has-text('Apply')"
    )
    if await submit_btn.count() == 0:
        return SubmitResult(
            submitted=False,
            application_id=packet.application_id,
            error="No submit button found on page",
        )

    await submit_btn.first.click()
    validated.consumed = True

    return SubmitResult(
        submitted=True,
        application_id=packet.application_id,
    )
