import asyncio
import structlog
from sqlalchemy import select

logger = structlog.get_logger()

async def match_jobs_against_profiles():
    """Match all jobs against all profiles."""
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import Job, UserProfile, MatchScore

    async with unit_of_work() as session:
        # Fetch jobs and profiles
        jobs_result = await session.execute(select(Job).limit(50))
        jobs = jobs_result.scalars().all()
        logger.info("fetched_jobs", count=len(jobs))

        profiles_result = await session.execute(select(UserProfile))
        profiles = profiles_result.scalars().all()
        logger.info("fetched_profiles", count=len(profiles))

        # Simple demo: create one match per job (placeholder)
        for job in jobs:
            if profiles:
                match = MatchScore(
                    job_id=job.id,
                    profile_id=profiles[0].id,
                    overall=0.85,
                    passed_prefilter=True,
                )
                session.add(match)

        await session.flush()
        logger.info("matching_complete", total=len(jobs))
        return {"total_matches": len(jobs), "jobs": len(jobs), "profiles": len(profiles)}

async def real_match(limit: int):
    """Real matching using the JobScoringService — validates real scoring, not placeholders.

    Args:
        limit: Number of top matches to score (small batch recommended for first test).

    Returns:
        Dict with summary including scored count, profile_id, and serialized report.
    """
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work
    from jobhunter.infrastructure.db.models import UserProfile
    from jobhunter.adapters.embedding.fastembed_embedder import FastEmbedEmbedder
    from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
    from jobhunter.adapters.scoring.llm_job_scorer import LlmJobScorer
    from jobhunter.application.services.prefilter import PreFilter
    from jobhunter.application.use_cases.job_scoring import JobScoringService
    from jobhunter.domain.scoring import WeightConfig
    from jobhunter.config import get_settings
    from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
    from jobhunter.infrastructure.repositories.match_score import SQLAlchemyMatchScoreRepository
    from jobhunter.infrastructure.repositories.user_profile import SQLAlchemyUserProfileRepository

    async with unit_of_work() as session:
        profile_result = await session.execute(select(UserProfile).limit(1))
        profile = profile_result.scalars().first()
        if not profile:
            logger.error("no_profile_found")
            raise RuntimeError("No UserProfile records exist in the database.")
        profile_id = profile.id

        settings = get_settings()
        tracker = UsageTracker(settings.llm_daily_call_cap)
        llm_client = GroqLlmClient(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            model=settings.groq_model,
            usage_tracker=tracker,
        )
        embedder = FastEmbedEmbedder(model_name=settings.embedding_model, dimension=settings.embedding_dimension)
        scorer = LlmJobScorer(llm_client=llm_client)

        service = JobScoringService(
            job_repo=SQLAlchemyJobRepository(session),
            match_score_repo=SQLAlchemyMatchScoreRepository(session),
            profile_repo=SQLAlchemyUserProfileRepository(session),
            embedder=embedder,
            scorer=scorer,
            prefilter=PreFilter(),
            weight_config=WeightConfig(),
            session=session,
            threshold=settings.match_score_threshold,
        )

        try:
            report = await service.score_jobs_for_profile(profile_id, limit=limit)
        except Exception as exc:
            logger.error("real_matching_failed", profile_id=str(profile_id), error=str(exc))
            raise

        scored = report.scored
        prefiltered = report.prefiltered_out
        above_threshold = report.above_threshold
        errors = report.scoring_errors
        top_results = report.top_results
        logger.info(
            "real_matching_summary",
            profile_id=str(profile_id),
            limit=limit,
            scored=scored,
            prefiltered=prefiltered,
            above_threshold=above_threshold,
            errors=errors,
            top_results=len(top_results),
        )
        return {
            "scored": scored,
            "prefiltered_out": prefiltered,
            "above_threshold": above_threshold,
            "scoring_errors": errors,
            "profile_id": str(profile_id),
            "limit": limit,
            "report": {
                "total_scored": scored,
                "top_results": [
                    {
                        "job_id": str(m.job_id),
                        "overall": m.overall,
                        "passed_prefilter": m.passed_prefilter,
                        "similarity": getattr(m, "similarity", None),
                        "rationale": m.rationale,
                    }
                    for m in top_results
                ],
            },
        }