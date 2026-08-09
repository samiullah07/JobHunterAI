"""Integration tests for JobScoringService — real DB on port 5433."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.application.services.prefilter import PreFilter
from jobhunter.application.use_cases.job_scoring import JobScoringService
from jobhunter.domain.enums import JobSource, RemotePolicy
from jobhunter.domain.scoring import WeightConfig
from jobhunter.infrastructure.db.models import Company, Job, Skill, UserProfile, WorkExperience
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.match_score import SQLAlchemyMatchScoreRepository
from jobhunter.infrastructure.repositories.user_profile import SQLAlchemyUserProfileRepository

pytestmark = pytest.mark.integration


async def _seed_profile(session: AsyncSession) -> uuid.UUID:
    profile = UserProfile(
        id=uuid.uuid4(),
        full_name="Test User",
        email="test@example.com",
        headline="Senior Python Engineer",
        summary="10 years of backend development.",
        location="NYC",
        remote_preference=RemotePolicy.REMOTE.value,
        salary_min=100000.0,
        salary_max=180000.0,
        salary_currency="USD",
    )
    session.add(profile)
    await session.flush()

    skill = Skill(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Python",
        category="Language",
        proficiency="Expert",
    )
    session.add(skill)

    exp = WorkExperience(
        id=uuid.uuid4(),
        profile_id=profile.id,
        company_name="BigTech",
        title="Staff Engineer",
        start_date=date(2018, 1, 1),
        is_current=True,
    )
    session.add(exp)
    await session.flush()
    return profile.id


async def _seed_jobs(session: AsyncSession) -> list[uuid.UUID]:
    """Seed 3 jobs: 1 that fails prefilter (low salary), 2 that pass."""
    company = Company(id=uuid.uuid4(), name="GoodCorp", is_blacklisted=False)
    session.add(company)
    await session.flush()

    bad_company = Company(id=uuid.uuid4(), name="BlacklistedCorp", is_blacklisted=True)
    session.add(bad_company)
    await session.flush()

    job_ids: list[uuid.UUID] = []

    # Job 1: passes prefilter (remote, good salary)
    j1 = Job(
        id=uuid.uuid4(),
        source=JobSource.GREENHOUSE.value,
        external_id="score-001",
        url="https://example.com/1",
        title="Backend Engineer",
        company_id=company.id,
        company_name="GoodCorp",
        location="Remote",
        remote_policy=RemotePolicy.REMOTE.value,
        salary_min=120000.0,
        salary_max=160000.0,
        description_raw="Python backend role with distributed systems.",
        fetched_at=datetime.now(UTC),
    )
    session.add(j1)
    job_ids.append(j1.id)

    # Job 2: fails prefilter (salary too low)
    j2 = Job(
        id=uuid.uuid4(),
        source=JobSource.LEVER.value,
        external_id="score-002",
        url="https://example.com/2",
        title="Junior Dev",
        company_id=company.id,
        company_name="GoodCorp",
        location="Onsite",
        remote_policy=RemotePolicy.ONSITE.value,
        salary_min=30000.0,
        salary_max=50000.0,
        description_raw="Entry-level role.",
        fetched_at=datetime.now(UTC),
    )
    session.add(j2)
    job_ids.append(j2.id)

    # Job 3: fails prefilter (blacklisted company)
    j3 = Job(
        id=uuid.uuid4(),
        source=JobSource.REMOTEOK.value,
        external_id="score-003",
        url="https://example.com/3",
        title="Senior Engineer",
        company_id=bad_company.id,
        company_name="BlacklistedCorp",
        location="Remote",
        remote_policy=RemotePolicy.REMOTE.value,
        salary_min=150000.0,
        salary_max=200000.0,
        description_raw="Great role but bad company.",
        fetched_at=datetime.now(UTC),
    )
    session.add(j3)
    job_ids.append(j3.id)

    await session.flush()
    return job_ids


class TestJobScoring:
    async def test_score_jobs_end_to_end(self, async_session: AsyncSession) -> None:
        from tests.fakes.embedder import FakeEmbedder
        from tests.fakes.scorer import FakeJobScorer

        profile_id = await _seed_profile(async_session)
        await _seed_jobs(async_session)
        await async_session.commit()

        job_repo = SQLAlchemyJobRepository(async_session)
        match_repo = SQLAlchemyMatchScoreRepository(async_session)
        profile_repo = SQLAlchemyUserProfileRepository(async_session)
        fake_scorer = FakeJobScorer()
        fake_embedder = FakeEmbedder()

        service = JobScoringService(
            job_repo=job_repo,
            match_score_repo=match_repo,
            profile_repo=profile_repo,
            embedder=fake_embedder,
            scorer=fake_scorer,
            prefilter=PreFilter(),
            weight_config=WeightConfig(),
            session=async_session,
            threshold=0.5,
        )

        report = await service.score_jobs_for_profile(profile_id, limit=50)

        # 3 jobs scored total
        assert report.scored == 3
        # Job 2 fails prefilter (onsite + low salary), Job 3 fails (blacklisted)
        assert report.prefiltered_out == 2
        # Only job 1 passes prefilter and gets LLM scoring
        assert fake_scorer.call_count == 1
        # Job 1 should be above threshold
        assert report.above_threshold >= 1

        # Verify MatchScore rows
        scores = await match_repo.list(limit=10)
        assert len(scores) == 3

        passing_scores = [s for s in scores if s.passed_prefilter]
        failing_scores = [s for s in scores if not s.passed_prefilter]
        assert len(passing_scores) == 1
        assert len(failing_scores) == 2

        for fs in failing_scores:
            assert fs.overall == 0.0
            assert fs.prefilter_reasons is not None
            assert any("FAIL" in r for r in fs.prefilter_reasons)

        ps = passing_scores[0]
        assert ps.overall > 0.0
        assert ps.components is not None
        assert ps.rationale is not None

    async def test_list_above_threshold(self, async_session: AsyncSession) -> None:
        from tests.fakes.embedder import FakeEmbedder
        from tests.fakes.scorer import FakeJobScorer

        profile_id = await _seed_profile(async_session)
        await _seed_jobs(async_session)
        await async_session.commit()

        job_repo = SQLAlchemyJobRepository(async_session)
        match_repo = SQLAlchemyMatchScoreRepository(async_session)
        profile_repo = SQLAlchemyUserProfileRepository(async_session)

        service = JobScoringService(
            job_repo=job_repo,
            match_score_repo=match_repo,
            profile_repo=profile_repo,
            embedder=FakeEmbedder(),
            scorer=FakeJobScorer(),
            prefilter=PreFilter(),
            weight_config=WeightConfig(),
            session=async_session,
            threshold=0.5,
        )

        await service.score_jobs_for_profile(profile_id)

        above = await match_repo.list_above_threshold(profile_id, 0.5)
        assert len(above) >= 1
        for s in above:
            assert s.overall >= 0.5

        ordered = [s.overall for s in above]
        assert ordered == sorted(ordered, reverse=True)

    async def test_malformed_scorer_does_not_store_zero_score(
        self, async_session: AsyncSession
    ) -> None:
        """A malformed LLM response must NOT create an all-zero MatchScore."""
        from jobhunter.adapters.scoring.llm_job_scorer import MalformedScoreError
        from jobhunter.domain.scoring import ScoreComponents
        from tests.fakes.embedder import FakeEmbedder

        profile_id = await _seed_profile(async_session)
        await _seed_jobs(async_session)
        await async_session.commit()

        class AlwaysMalformedScorer:
            """Raises MalformedScoreError on every call."""

            def __init__(self) -> None:
                self.call_count = 0

            async def score(self, job: object, profile: object) -> tuple[ScoreComponents, str]:
                self.call_count += 1
                raise MalformedScoreError("simulated malformed LLM output")

        malformed_scorer = AlwaysMalformedScorer()

        job_repo = SQLAlchemyJobRepository(async_session)
        match_repo = SQLAlchemyMatchScoreRepository(async_session)
        profile_repo = SQLAlchemyUserProfileRepository(async_session)

        service = JobScoringService(
            job_repo=job_repo,
            match_score_repo=match_repo,
            profile_repo=profile_repo,
            embedder=FakeEmbedder(),
            scorer=malformed_scorer,
            prefilter=PreFilter(),
            weight_config=WeightConfig(),
            session=async_session,
            threshold=0.5,
        )

        report = await service.score_jobs_for_profile(profile_id, limit=50)

        # Batch completed without crashing
        assert report.scored == 3
        # 2 jobs fail prefilter (no scorer call), 1 passes prefilter → scorer called
        assert malformed_scorer.call_count == 1
        assert report.scoring_errors == 1
        assert report.prefiltered_out == 2

        # Only prefilter-failed rows should be stored (the malformed one is skipped)
        scores = await match_repo.list(limit=10)
        assert len(scores) == 2
        for s in scores:
            assert s.passed_prefilter is False
            assert s.overall == 0.0
