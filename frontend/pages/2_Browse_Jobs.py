"""Browse all discovered jobs - generate CV/cover on demand."""
import streamlit as st
import asyncio
import json

def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def load_all_jobs(page, per_page, source_filter, keyword="", sort_by="newest"):
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import Job, ResumeVersion, UserProfile, MatchScore
    from sqlalchemy import select, func, outerjoin, nulls_last

    async with unit_of_work() as session:
        # Fetch the active (first) profile for existing score checks and fit-sorting
        profile_result = await session.execute(select(UserProfile).limit(1))
        profile = profile_result.scalars().first()

        # Build base query
        base = select(Job)
        if keyword:
            base = base.where(Job.title.ilike(f"%{keyword}%"))
        if source_filter and source_filter != "All":
            base = base.where(Job.source == source_filter)

        # Get total count
        total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar()

        # Execute query with pagination
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

            existing_overall = None
            if profile:
                ms = (await session.execute(
                    select(MatchScore).where(
                        MatchScore.job_id == j.id,
                        MatchScore.profile_id == profile.id,
                    ).order_by(MatchScore.created_at.desc()).limit(1)
                )).scalars().first()
                if ms is not None:
                    existing_overall = ms.overall

            job_list.append({
                "id": str(j.id),
                "title": j.title or "Untitled",
                "company": j.company_name or "Unknown",
                "location": j.location or "Remote",
                "source": j.source if isinstance(j.source, str) else (j.source.value if j.source else "unknown"),
                "url": j.url or "",
                "has_resume": has_resume,
                "existing_overall": existing_overall,
            })

        # Sort by fit score if requested
        if sort_by == "fit":
            # Put jobs with a score first, then sort by score descending
            job_list.sort(key=lambda x: -(x["existing_overall"] if x["existing_overall"] is not None else -1.0))

        return {"jobs": job_list, "total": total, "pages": max(1, (total + per_page - 1) // per_page)}


async def load_job_scores(job_ids, profile_id):
    """Load existing MatchScore entries for given jobs (read-only, no LLM)."""
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import MatchScore
    from sqlalchemy import select
    from uuid import UUID

    async with unit_of_work() as session:
        result = await session.execute(
            select(MatchScore)
            .where(
                MatchScore.job_id.in_([UUID(jid) for jid in job_ids]),
                MatchScore.profile_id == profile_id,
            )
        )
        scores = result.scalars().all()
    score_map = {}
    for score in scores:
        score_map[str(score.job_id)] = {
            "overall": score.overall,
            "rationale": score.rationale,
            "passed_prefilter": score.passed_prefilter,
        }
    return score_map


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
    llm = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
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


async def score_one_job(job_id_str):
    """Score a single job against the active profile using the real LLM-based scorer."""
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import Job, UserProfile, MatchScore
    from jobhunter.config import get_settings
    from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
    from jobhunter.adapters.scoring.llm_job_scorer import LlmJobScorer, MalformedScoreError
    from jobhunter.domain.scoring import WeightConfig
    from pydantic import ValidationError
    from sqlalchemy import select, delete
    from sqlalchemy.orm import selectinload
    from uuid import UUID

    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
    scorer = LlmJobScorer(llm_client=llm)
    weights = WeightConfig()

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
            components, rationale = await scorer.score(job, profile)
        except (MalformedScoreError, ValidationError) as exc:
            return {"error": f"Scoring failed: {exc}"}
        except Exception as exc:
            # Catch rate-limit (429) and other API errors gracefully
            return {"error": f"Scoring error: {exc}"}

        # Compute overall using the same WeightConfig as JobScoringService
        overall = weights.compute_overall(components)

        # Delete any existing score for this job+profile, then insert fresh
        await session.execute(
            delete(MatchScore).where(
                MatchScore.job_id == job.id,
                MatchScore.profile_id == profile.id,
            )
        )
        score_row = MatchScore(
            job_id=job.id,
            profile_id=profile.id,
            overall=overall,
            components=components.model_dump(),
            rationale=rationale,
            passed_prefilter=True,
        )
        session.add(score_row)
        await session.flush()
        return {
            "success": True,
            "overall": overall,
            "rationale": rationale,
            "title": job.title,
            "company": job.company_name,
        }


st.title("Browse Jobs")
st.markdown("All discovered jobs - generate tailored CV and cover letter on demand")

# === UI Controls ===
col1, col2, col3 = st.columns([2, 2, 1])

source_filter = col1.selectbox("Filter by source", ["All", "GREENHOUSE", "LEVER", "REMOTEOK"])
per_page = col2.selectbox("Jobs per page", [10, 25, 50], index=0)
page = col3.number_input("Page", min_value=1, value=1, step=1)

keyword = st.text_input("Search job titles", placeholder="e.g., data analyst, machine learning")
sort_by = st.selectbox("Sort by", ["newest", "fit"], index=0,
                       format_func=lambda x: "Newest first" if x=="newest" else "Best fit first")

# Reset page when a keyword is entered to start from the first page
if keyword:
    page = 1

try:
    data = _run_async(load_all_jobs(page, per_page, source_filter, keyword, sort_by))
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

        # "Score This Job" button — uses real LLM scorer
        if c4.button(f"Score {job['title']}", key=f"score_{job['id']}", type="primary"):
            with st.spinner(f"Scoring {job['title']}..."):
                score_result = _run_async(score_one_job(job["id"]))
            if "error" in score_result:
                st.error(score_result["error"])
            else:
                pct = int(score_result["overall"] * 100)
                st.success(f"Fit Score: {pct}% — {job['title']}")
                st.info(score_result["rationale"])

    st.divider()