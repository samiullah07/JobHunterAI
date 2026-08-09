"""Job scoring use case — prefilter + embedding + LLM scoring."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog

from jobhunter.adapters.scoring.llm_job_scorer import MalformedScoreError
from jobhunter.application.services.prefilter import PreFilter, cosine_similarity
from jobhunter.domain.scoring import MatchResult, ScoreComponents, ScoringReport, WeightConfig
from jobhunter.infrastructure.db.models import MatchScore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.application.ports.embedder import Embedder
    from jobhunter.application.ports.job_scorer import JobScorer
    from jobhunter.application.repositories.job import JobRepository
    from jobhunter.application.repositories.match_score import MatchScoreRepository
    from jobhunter.application.repositories.user_profile import UserProfileRepository

logger = structlog.get_logger()


def _render_profile_for_embedding(profile: object) -> str:
    """Render a text representation of the profile for embedding."""
    from jobhunter.infrastructure.db.models import UserProfile

    p: UserProfile = profile  # type: ignore[assignment]
    parts = [p.full_name, p.headline or "", p.summary or ""]
    if p.skills:
        parts.append(" ".join(s.name for s in p.skills))
    if p.work_experiences:
        for exp in p.work_experiences:
            parts.append(f"{exp.title} {exp.company_name}")
            if exp.technologies:
                parts.append(" ".join(exp.technologies))
    if p.keywords:
        parts.append(" ".join(p.keywords))
    return " ".join(parts)


class JobScoringService:
    """Orchestrates pre-filtering, embedding, LLM scoring, and persistence."""

    def __init__(
        self,
        job_repo: JobRepository,
        match_score_repo: MatchScoreRepository,
        profile_repo: UserProfileRepository,
        embedder: Embedder,
        scorer: JobScorer,
        prefilter: PreFilter,
        weight_config: WeightConfig,
        session: AsyncSession,
        threshold: float = 0.75,
    ) -> None:
        self._job_repo = job_repo
        self._match_score_repo = match_score_repo
        self._profile_repo = profile_repo
        self._embedder = embedder
        self._scorer = scorer
        self._prefilter = prefilter
        self._weights = weight_config
        self._session = session
        self._threshold = threshold

    async def score_jobs_for_profile(self, profile_id: uuid.UUID, limit: int = 50) -> ScoringReport:
        profile = await self._profile_repo.get_with_children(profile_id)
        if profile is None:
            msg = f"Profile {profile_id} not found"
            raise ValueError(msg)

        jobs = await self._job_repo.list_unscored(profile_id, limit=limit)

        profile_text = _render_profile_for_embedding(profile)
        profile_embedding = await self._embedder.embed(profile_text)

        report = ScoringReport()
        results: list[MatchResult] = []

        for job in jobs:
            result = await self._score_one(job, profile, profile_id, profile_embedding, report)
            report.scored += 1
            if result is None:
                report.scoring_errors += 1
            elif not result.passed_prefilter:
                report.prefiltered_out += 1
            elif result.overall >= self._threshold:
                report.above_threshold += 1
            if result is not None:
                results.append(result)

        await self._session.commit()

        results.sort(key=lambda r: r.overall, reverse=True)
        report.top_results = results[:10]
        return report

    async def _score_one(
        self,
        job: object,
        profile: object,
        profile_id: uuid.UUID,
        profile_embedding: list[float],
        report: ScoringReport,
    ) -> MatchResult | None:
        from jobhunter.infrastructure.db.models import Job, UserProfile

        j: Job = job  # type: ignore[assignment]
        p: UserProfile = profile  # type: ignore[assignment]

        company = j.company
        passed, reasons = self._prefilter.check(j, p, company)

        if not passed:
            match_score = MatchScore(
                job_id=j.id,
                profile_id=profile_id,
                overall=0.0,
                components=ScoreComponents().model_dump(),
                rationale="Pre-filter failed: " + "; ".join(reasons),
                passed_prefilter=False,
                prefilter_reasons=reasons,
            )
            async with self._session.begin_nested():
                self._session.add(match_score)
                await self._session.flush()
            return MatchResult(
                job_id=j.id,
                profile_id=profile_id,
                overall=0.0,
                components=ScoreComponents(),
                rationale=match_score.rationale or "",
                passed_prefilter=False,
                prefilter_reasons=reasons,
            )

        if j.embedding is None:
            job_text = f"{j.title} {j.company_name} {j.description_raw[:2000]}"
            j.embedding = await self._embedder.embed(job_text)
            async with self._session.begin_nested():
                await self._session.flush()

        similarity = cosine_similarity(profile_embedding, list(j.embedding))

        try:
            components, rationale = await self._scorer.score(j, p)
        except MalformedScoreError:
            logger.warning("scoring_malformed_skipped", job_id=str(j.id))
            return None

        overall = self._weights.compute_overall(components)

        match_score = MatchScore(
            job_id=j.id,
            profile_id=profile_id,
            overall=overall,
            components=components.model_dump(),
            rationale=rationale,
            passed_prefilter=True,
            prefilter_reasons=reasons,
            similarity=similarity,
        )
        async with self._session.begin_nested():
            self._session.add(match_score)
            await self._session.flush()

        return MatchResult(
            job_id=j.id,
            profile_id=profile_id,
            overall=overall,
            components=components,
            rationale=rationale,
            passed_prefilter=True,
            prefilter_reasons=reasons,
        )
