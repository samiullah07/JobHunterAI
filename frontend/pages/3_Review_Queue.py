"""Human-in-the-loop review UI — Streamlit MVP.

Displays the approval queue and full review panel for each application.
APPROVE mints an ApprovalToken bound to the packet's fill_hash — it NEVER
submits the application (submission is wired in a later milestone).

Production upgrade: Next.js frontend (planned for M12+).
Run: `uv run streamlit run frontend/review_app.py`
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any
from jobhunter.frontend_data.sync_reader import load_review_queue

if TYPE_CHECKING:
    from jobhunter.domain.review import ApplicationReviewView, ReviewOutcome


def _run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """Bridge for calling async code from Streamlit's sync context.
    Forces a fresh event loop for each call to avoid shared connection issues.
    """
    # Create a fresh event loop (don't reuse Streamlit's shared loop)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.close()
        except Exception:
            pass


def render_warnings(view: ApplicationReviewView) -> None:
    """Render prominent warnings for blockers and fabrication violations."""
    import streamlit as st

    if view.has_blocking_issues:
        st.error("**ACTION REQUIRED — Issues detected. Review carefully before approving.**")

    if view.blockers:
        with st.container():
            st.markdown("### Blockers")
            for blocker in view.blockers:
                st.warning(f"**{blocker.kind}**: {blocker.detail}")

    if view.fabrication_report_resume and not view.fabrication_report_resume.is_clean:
        st.error("**Resume Fabrication Violations:**")
        for v in view.fabrication_report_resume.violations:
            st.markdown(f"- {v}")

    if view.fabrication_report_cover_letter and not view.fabrication_report_cover_letter.is_clean:
        st.error("**Cover Letter Fabrication Violations:**")
        for v in view.fabrication_report_cover_letter.violations:
            st.markdown(f"- {v}")


def render_job_summary(view: ApplicationReviewView) -> None:
    """Render the job summary header."""
    import streamlit as st

    cols = st.columns([2, 1, 1, 1])
    with cols[0]:
        st.markdown(f"### {view.role}")
        st.markdown(f"**{view.company}**")
    with cols[1]:
        st.metric("Match", f"{view.match_score:.0%}" if view.match_score else "N/A")
    with cols[2]:
        st.markdown(f"**Location**\n\n{view.location or 'Remote/Unknown'}")
    with cols[3]:
        st.markdown(f"**Salary**\n\n{view.salary or 'Not listed'}")


def render_action_buttons(view: ApplicationReviewView) -> str | None:
    """Render the 5 decision buttons. Returns the chosen action or None."""
    import streamlit as st

    cols = st.columns(5)
    action: str | None = None

    has_issues = view.has_blocking_issues
    approve_label = "Override & Approve" if has_issues else "Approve"

    with cols[0]:
        if has_issues:
            if st.button(approve_label, type="secondary", use_container_width=True):
                action = "approve_override"
        else:
            if st.button(approve_label, type="primary", use_container_width=True):
                action = "approve"
    with cols[1]:
        if st.button("Reject", type="secondary", use_container_width=True):
            action = "reject"
    with cols[2]:
        if st.button("Edit", use_container_width=True):
            action = "edit"
    with cols[3]:
        if st.button("Regenerate", use_container_width=True):
            action = "regenerate"
    with cols[4]:
        if st.button("Skip", use_container_width=True):
            action = "skip"

    return action


def render_artifacts(view: ApplicationReviewView) -> None:
    """Render resume, cover letter, filled answers, uploads, screenshots."""
    import streamlit as st

    # Resume
    with st.expander("Resume Preview", expanded=True):
        if view.resume_preview_markdown:
            st.markdown(view.resume_preview_markdown)
        else:
            st.info("No resume version linked.")

    # Cover letter
    with st.expander("Cover Letter Preview", expanded=True):
        if view.cover_letter_preview_markdown:
            st.markdown(view.cover_letter_preview_markdown)
        else:
            st.info("No cover letter version linked.")

    # Filled form answers
    if view.filled_fields:
        with st.expander("Filled Form Answers", expanded=False):
            rows = [
                {"Field": f.label, "Value": f.value, "Source": f.source} for f in view.filled_fields
            ]
            st.table(rows)

    # Uploaded files
    if view.uploaded_files:
        with st.expander("Uploaded Files", expanded=False):
            for f in view.uploaded_files:
                st.markdown(f"- `{f}`")

    # Screenshots
    if view.screenshot_keys:
        with st.expander("Screenshots", expanded=False):
            for key in view.screenshot_keys:
                st.markdown(f"- `{key}`")


def handle_decision(action: str, application_id: str, approved_by: str) -> ReviewOutcome | None:
    """Call the review service to record the decision."""
    from jobhunter.application.use_cases.review import ReviewService
    from jobhunter.domain.review import ReviewDecision, ReviewRefused
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work

    decision_map = {
        "approve": ReviewDecision.APPROVE,
        "approve_override": ReviewDecision.APPROVE,
        "reject": ReviewDecision.REJECT,
        "edit": ReviewDecision.EDIT,
        "regenerate": ReviewDecision.REGENERATE,
        "skip": ReviewDecision.SKIP,
    }
    decision = decision_map[action]
    override = action == "approve_override"

    async def _record() -> ReviewOutcome:
        async with unit_of_work() as session:
            service = ReviewService(session)
            return await service.record_decision(
                application_id=application_id,
                decision=decision,
                approved_by=approved_by if decision == ReviewDecision.APPROVE else None,
                override=override,
            )

    import streamlit as st

    try:
        outcome = _run_async(_record())
    except ReviewRefused as exc:
        st.error(f"Approval refused: {exc.reason}")
        return None
    return outcome


def render_outcome(outcome: ReviewOutcome) -> None:
    """Show the result of the decision."""
    import streamlit as st

    if outcome.decision == "approve" and outcome.token:
        st.success(
            f"**Approved** — Token minted (nonce: `{outcome.token.nonce[:8]}...`)\n\n"
            f"fill_hash: `{outcome.token.fill_hash[:16]}...`\n\n"
            "Ready for submission (submission wired in a later step — "
            "**nothing was submitted**)."
        )
    elif outcome.decision == "reject":
        st.warning("**Rejected** — Application moved to rejected status.")
    elif outcome.decision == "skip":
        st.info("**Skipped** — Application moved to skipped status.")
    elif outcome.decision in ("edit", "regenerate"):
        st.info(f"**{outcome.decision.title()}** requested — artifacts queued for rework.")
    elif outcome.refused:
        st.error(f"Decision refused: {outcome.refusal_reason}")


def load_review_view(application_id: str) -> ApplicationReviewView | None:
    """Load the full review view for an application."""
    from jobhunter.application.use_cases.review import ReviewService
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work

    async def _load() -> ApplicationReviewView | None:
        async with unit_of_work() as session:
            service = ReviewService(session)
            return await service.build_review_view(application_id)

    return _run_async(_load())


def main() -> None:
    """Streamlit app entrypoint."""
    import streamlit as st

    st.set_page_config(page_title="JobHunter — Review", layout="wide")
    st.title("Application Review")

    # Sidebar: approval queue
    st.sidebar.header("Review Queue")
    try:
        queue = load_review_queue()
    except Exception as exc:
        st.sidebar.error(f"Cannot load queue: {exc}")
        queue = []

    if not queue:
        st.sidebar.info("No applications ready for review.")
        st.info(
            "No applications in the review queue. Applications will appear here "
            "once they reach READY_FOR_REVIEW status."
        )
        return

    selected_id = st.sidebar.radio(
        "Select application:",
        options=[item["id"] for item in queue],
        format_func=lambda x: next(f"{q['company']} — {q['role']}" for q in queue if q["id"] == x),
    )

    if not selected_id:
        return

    # Load full review view
    view = load_review_view(selected_id)
    if view is None:
        st.error("Application not found.")
        return

    # 1. Job summary
    render_job_summary(view)
    st.divider()

    # 2. Action buttons + reviewer name
    approved_by = st.text_input("Reviewer name", value="human", key="reviewer_name")
    action = render_action_buttons(view)
    st.divider()

    # 3. Prominent warnings (always visible, never collapsed)
    render_warnings(view)
    st.divider()

    # 4. Artifacts
    render_artifacts(view)

    # Handle decision
    if action:
        outcome = handle_decision(action, selected_id, approved_by)
        if outcome:
            render_outcome(outcome)
            st.rerun()


if __name__ == "__main__":
    main()
