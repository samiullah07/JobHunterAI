import streamlit as st
import asyncio

st.set_page_config(
    page_title="AI Job Hunter",
    page_icon="🎯",
    layout="wide",
)

st.sidebar.title("AI Job Hunter")
st.sidebar.markdown("Your autonomous job-hunting assistant")
st.sidebar.divider()

st.title("Welcome to AI Job Hunter")
st.markdown("""
This tool helps you find jobs, generate tailored CVs and cover letters, and apply.

**How to use it:**
1. **My Profile** — enter your details (name, skills, experience)
2. **Browse Jobs** — see all discovered jobs, generate a tailored CV for any of them
3. **Review Queue** — review and approve your applications
4. **My Applications** — get apply links and download your CV/cover letters

Use the sidebar to navigate between pages.
""")


# === _run_async helper ===
def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# === Pipeline status helpers ===
async def check_profile_exists():
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from sqlalchemy import select, func
    from jobhunter.infrastructure.db.models import UserProfile
    async with unit_of_work() as session:
        count = (await session.execute(select(func.count()).select_from(UserProfile))).scalar()
        return count > 0


async def get_stats():
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from sqlalchemy import select, func
    from jobhunter.infrastructure.db.models import Job, Application, MatchScore
    async with unit_of_work() as session:
        jobs = (await session.execute(select(func.count()).select_from(Job))).scalar()
        apps = (await session.execute(select(func.count()).select_from(Application))).scalar()
        return {"jobs": jobs, "applications": apps}


# === Pipeline UI Section ===
st.divider()

# Show current stats
try:
    stats = _run_async(get_stats())
    col1, col2 = st.columns(2)
    col1.metric("Jobs Discovered", stats["jobs"])
    col2.metric("Applications", stats["applications"])
except Exception:
    pass  # stats are nice-to-have, don't crash if DB is down

st.divider()

# Profile check + Find Jobs button
has_profile = False
try:
    has_profile = _run_async(check_profile_exists())
except Exception as exc:
    import logging; logging.warning(f'Profile check failed: {type(exc).__name__}: {exc}')

if not has_profile:
    st.warning("No profile found. Please upload your CV or fill in your details on the My Profile page first.")
else:
    st.subheader("Ready to find jobs?")

    gen_limit = st.slider("How many CVs to generate", min_value=1, max_value=10, value=5)

    if st.button("Find Jobs for Me", type="primary"):
        with st.status("Running pipeline...", expanded=True) as status:
            st.write("Starting job discovery pipeline...")

            async def run_with_progress():
                from jobhunter.workers.pipeline import run_full_pipeline
                return await run_full_pipeline(generation_limit=gen_limit)

            try:
                result = _run_async(run_with_progress())

                if "discover" in result.steps_completed:
                    st.write("Step 1: Discovery complete")
                if "generate" in result.steps_completed:
                    st.write(f"Step 2: Generated {result.generation.get('generated', 0) if result.generation else 0} CVs")
                if "queue" in result.steps_completed:
                    st.write(f"Step 3: Queued {result.queueing.get('queued', 0) if result.queueing else 0} applications")

                if result.success:
                    status.update(label="Pipeline complete!", state="complete")
                    st.success("Done! Go to Browse Jobs to score and review, or Review Queue to approve applications.")
                    st.balloons()
                else:
                    status.update(label="Pipeline completed with errors", state="error")
                    st.warning(f"Some steps failed: {result.steps_failed}. Partial results are available.")
                    if result.error:
                        st.error(f"Error: {result.error}")
            except Exception as exc:
                status.update(label="Pipeline failed", state="error")
                st.error(f"Pipeline error: {type(exc).__name__}. Check terminal for details.")
