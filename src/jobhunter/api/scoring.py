"""Scoring API router — trigger scoring and list matches."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.adapters.embedding.fastembed_embedder import FastEmbedEmbedder
from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
from jobhunter.adapters.scoring.llm_job_scorer import LlmJobScorer
from jobhunter.application.ports.embedder import Embedder
from jobhunter.application.ports.job_scorer import JobScorer
from jobhunter.application.services.prefilter import PreFilter
from jobhunter.application.use_cases.job_scoring import JobScoringService
from jobhunter.config import get_settings
from jobhunter.domain.scoring import ScoringReport, WeightConfig
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.match_score import SQLAlchemyMatchScoreRepository
from jobhunter.infrastructure.repositories.user_profile import SQLAlchemyUserProfileRepository

router = APIRouter(prefix="/profiles", tags=["scoring"])


def _get_scoring_service(session: AsyncSession = Depends(get_session)) -> JobScoringService:  # noqa: B008
    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm_client = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
    embedder: Embedder = FastEmbedEmbedder(
        model_name=settings.embedding_model, dimension=settings.embedding_dimension
    )
    scorer: JobScorer = LlmJobScorer(llm_client=llm_client)

    return JobScoringService(
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


@router.post("/{profile_id}/score")
async def score_jobs(
    profile_id: uuid.UUID,
    limit: int = 50,
    service: JobScoringService = Depends(_get_scoring_service),  # noqa: B008
) -> ScoringReport:
    try:
        return await service.score_jobs_for_profile(profile_id, limit=min(limit, 200))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{profile_id}/matches")
async def list_matches(
    profile_id: uuid.UUID,
    threshold: float = 0.75,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[dict[str, object]]:
    repo = SQLAlchemyMatchScoreRepository(session)
    scores = await repo.list_above_threshold(profile_id, threshold, limit=min(limit, 200))
    return [
        {
            "id": str(s.id),
            "job_id": str(s.job_id),
            "profile_id": str(s.profile_id),
            "overall": s.overall,
            "components": s.components,
            "rationale": s.rationale,
            "passed_prefilter": s.passed_prefilter,
            "similarity": s.similarity,
        }
        for s in scores
    ]
