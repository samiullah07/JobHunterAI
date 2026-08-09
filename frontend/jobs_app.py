"""Browse all discovered jobs - generate CV/cover on demand."""
import streamlit as st
import asyncio
import json

st.set_page_config(page_title="Browse Jobs", page_icon="", layout="wide")

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def load_all_jobs(page, per_page, source_filter):
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import Job, ResumeVersion
    from sqlalchemy import select, func, text
    async with unit_of_work() as session:
        base = select(Job)
        if source_filter and source_filter != "All":
            base = base.where(Job.source == source_filter)
        total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar()
        jobs_result = await session.execute(
            base.order_by(Job.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        jobs = jobs_result.scalars().all()
        job_list = []
        for j in jobs:
            has_resume = (await session.execute(
                select(func.count()).select_from(ResumeVersion).where(ResumeVersion.job_id == j.id)
            )).scalar() > 0
            job_list.append({
                "id": str(j.id),
                "title": j.title or "Untitled",
                "company": j.company_name or "Unknown",
                "location": j.location or "Remote",
                "source": j.source if isinstance(j.source, str) else (j.source.value if j.source else "unknown"),
                "url": j.url or "",
                "has_resume": has_resume,
            })
        return {"jobs": job_list, "total": total, "pages": max(1, (total + per_page - 1) // per_page)}

async def generate_for_job(job_id_str):
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import Job, UserProfile, ResumeVersion, CoverLetterVersion
    from jobhunter.config import get_settings
    from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
    from jobhunter.adapters.generation.llm_resume_generator import LlmResumeGenerator, MalformedResumeError
    from jobhunter.adapters.generation.llm_cover_letter_generator import LlmCoverLetterGenerator, MalformedCoverLetterError
    from pydantic import ValidationError
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from uuid import UUID
    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(api_key=settings.groq_api_key, base_url=settings.groq_base_url, model=settings.groq_model, usage_tracker=tracker)
    resume_gen = LlmResumeGenerator(llm_client=llm)
    cover_gen = LlmCoverLetterGenerator(llm_client=llm)
    async with unit_of_work() as session:
        job = await session.get(Job, UUID(job_id_str))
        if not job:
            return {"error": "Job not found"}
        profile_result = await session.execute(
            select(UserProfile).options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.work_experiences),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.projects),
                selectinload(UserProfile.certifications),
            ).limit(1)
        )
        profile = profile_result.scalars().first()
        if not profile:
            return {"error": "No profile found. Create one first."}
        try:
            tailored = await resume_gen.generate(profile, job)
        except (MalformedResumeError, ValidationError) as exc:
            return {"error": f"Resume generation failed: {exc}"}
        resume = ResumeVersion(
            profile_id=profile.id, job_id=job.id,
            version_label=f"Tailored for {job.title}",
            canonical_json=tailored.model_dump(mode="json"),
            storage_keys={"json": f"resumes/auto/{job.id}.json"},
        )
        session.add(resume)
        try:
            cover_obj = await cover_gen.generate(profile, job)
        except (MalformedCoverLetterError, ValidationError) as exc:
            return {"error": f"Cover letter generation failed: {exc}"}
        body_md = (
            cover_obj.salutation + "\n\n"
            + cover_obj.opening + "\n\n"
            + "\n\n".join(cover_obj.body_paragraphs) + "\n\n"
            + cover_obj.closing + "\n\n"
            + cover_obj.signature
        )
        cover = CoverLetterVersion(
            profile_id=profile.id, job_id=job.id,
            version_label=f"Tailored cover for {job.title}",
            body_markdown=body_md,
            storage_keys={"markdown": f"covers/auto/{job.id}.md"},
        )
        session.add(cover)
        await session.flush()
        return {"success": True, "title": job.title, "company": job.company_name}

st.title("Browse Jobs")
st.markdown("All discovered jobs - generate tailored CV and cover letter on demand")

col1, col2, col3 = st.columns([2, 2, 1])
source_filter = col1.selectbox("Filter by source", ["All", "GREENHOUSE", "LEVER", "REMOTEOK"])
per_page = col2.selectbox("Jobs per page", [10, 25, 50], index=0)
page = col3.number_input("Page", min_value=1, value=1, step=1)

try:
    data = _run_async(load_all_jobs(page, per_page, source_filter))
except Exception as e:
    st.error(f"Failed to load jobs: {e}")
    data = {"jobs": [], "total": 0, "pages": 1}

st.caption(f"Showing page {page} of {data['pages']} ({data['total']} total jobs)")
st.divider()

for job in data["jobs"]:
    with st.container():
        c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
        c1.markdown(f"**{job['title']}**")
        c1.caption(f"{job['company']} - {job['location']}")
        c2.caption(f"Source: {job['source']}")
        if job["url"]:
            c3.link_button("View Job", job["url"], type="secondary")
        if job["has_resume"]:
            c4.success("CV Ready", icon="✅")
        else:
            if c4.button("Generate CV", key=f"gen_{job['id']}", type="primary"):
                with st.spinner(f"Generating CV + Cover for {job['title']}..."):
                    result = _run_async(generate_for_job(job["id"]))
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success(f"Generated CV + Cover for {result['title']} at {result['company']}")
                    st.rerun()
    st.divider()
