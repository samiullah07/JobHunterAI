"""
Resume + Cover letter generation worker for top job matches.

This is a minimal placeholder pipeline — real generation will use
the LLM-based adapters once integrated.
"""

import asyncio
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = structlog.get_logger()


async def generate_for_top_matches(limit: int = 3):
    """
    Generate resume + cover versions for the top N match scores.

    Args:
        limit: Number of top-scored matches to process.

    Returns:
        Dict summarizing how many resumes/covers were generated.
    """
    # Imports kept inside the coroutine so the module stays lightweight
    # and the DB/ORM stack is only loaded when actually needed.
    from jobhunter.infrastructure.db.models import (
        MatchScore,
        Job,
        UserProfile,
        ResumeVersion,
        CoverLetterVersion,
    )
    from jobhunter.config import get_settings
    from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
    from jobhunter.adapters.generation.llm_resume_generator import LlmResumeGenerator, MalformedResumeError
    from jobhunter.adapters.generation.llm_cover_letter_generator import LlmCoverLetterGenerator, MalformedCoverLetterError
    from pydantic import ValidationError
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work

    # Build the Groq LLM client + generators once (pattern from api/resumes.py)
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
        # 1. Try match_scores first; fall back to newest jobs if no scores exist
        result = await session.execute(
            select(MatchScore)
            .where(MatchScore.passed_prefilter == True)  # noqa: E712
            .order_by(MatchScore.overall.desc())
            .limit(limit)
        )
        matches = result.scalars().all()
        logger.info("top_matches_fetched", count=len(matches))

        # Build list of (job, profile) pairs to generate for
        job_profile_pairs = []
        if matches:
            for match in matches:
                j = await session.get(Job, match.job_id)
                job_profile_pairs.append((j, match.profile_id))
        else:
            # Fallback: pick newest jobs that don't already have a resume
            logger.info("no_match_scores_found", fallback="newest_jobs")
            from sqlalchemy import and_, exists
            has_resume = exists(
                select(ResumeVersion.id).where(ResumeVersion.job_id == Job.id)
            )
            fallback_result = await session.execute(
                select(Job)
                .where(~has_resume)
                .order_by(Job.created_at.desc())
                .limit(limit)
            )
            fallback_jobs = fallback_result.scalars().all()
            # Get the single active profile
            p_result = await session.execute(select(UserProfile.id).limit(1))
            p_id = p_result.scalar_one_or_none()
            if p_id and fallback_jobs:
                for j in fallback_jobs:
                    job_profile_pairs.append((j, p_id))
            logger.info("fallback_jobs_selected", count=len(job_profile_pairs))

        generated = 0
        for job, profile_id in job_profile_pairs:
            # Eagerly load profile with all relationships accessed by LLM generator to avoid lazy-load errors
            profile = await session.execute(
                select(UserProfile)
                .options(
                    selectinload(UserProfile.skills),
                    selectinload(UserProfile.work_experiences),
                    selectinload(UserProfile.educations),
                    selectinload(UserProfile.projects),
                    selectinload(UserProfile.certifications)
                )
                .where(UserProfile.id == profile_id)
            )
            profile = profile.scalar_one_or_none()

            if profile is None:
                logger.warning("profile_not_found", profile_id=str(match.profile_id))
                continue

            # 2. Generate REAL tailored resume via LLM
            try:
                tailored = await resume_gen.generate(profile, job)
            except (MalformedResumeError, ValidationError) as exc:
                logger.warning("resume_generation_failed", job_id=str(job.id), error=str(exc))
                continue

            resume = ResumeVersion(
                profile_id=profile.id,
                job_id=job.id,
                version_label=f"Tailored for {job.title}",
                canonical_json=tailored.model_dump(mode="json"),
                storage_keys={"json": f"resumes/auto/{job.id}.json"},
            )
            session.add(resume)

            # 3. Generate REAL tailored cover letter via LLM
            try:
                cover_obj = await cover_gen.generate(profile, job)
            except (MalformedCoverLetterError, ValidationError) as exc:
                logger.warning("cover_generation_failed", job_id=str(job.id), error=str(exc))
                continue

            body_md = (
                cover_obj.salutation + "\n\n"
                + cover_obj.opening + "\n\n"
                + "\n\n".join(cover_obj.body_paragraphs) + "\n\n"
                + cover_obj.closing + "\n\n"
                + cover_obj.signature
            )

            cover = CoverLetterVersion(
                profile_id=profile.id,
                job_id=job.id,
                version_label=f"Tailored cover for {job.title}",
                body_markdown=body_md,
                storage_keys={"markdown": f"covers/auto/{job.id}.md"},
            )
            session.add(cover)

            generated += 1
            # Sanitize logging to avoid Unicode encoding issues in Windows console
            # Replace NEL (U+0085) and other problematic control chars
            safe_title = (
                job.title.replace("", " ")
                if job.title
                else f"Generated_{job.id}"
            )
            safe_company = (
                job.company_name.replace("", " ")
                if job.company_name
                else "Unknown"
            )
            logger.info(
                "generated_for_match",
                job_title=safe_title,
                company=safe_company,
            )

        await session.flush()
        logger.info("generation_complete", generated=generated)
        return {"generated": generated, "matches_processed": len(matches)}
