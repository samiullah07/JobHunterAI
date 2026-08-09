"""API tests for /profiles/{id}/score and /profiles/{id}/matches — all offline."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, date, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.api.scoring import _get_scoring_service
from jobhunter.application.services.prefilter import PreFilter
from jobhunter.application.use_cases.job_scoring import JobScoringService
from jobhunter.domain.enums import JobSource, RemotePolicy
from jobhunter.domain.scoring import WeightConfig
from jobhunter.infrastructure.db.models import Company, Job, Skill, UserProfile, WorkExperience
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.match_score import SQLAlchemyMatchScoreRepository
from jobhunter.infrastructure.repositories.user_profile import SQLAlchemyUserProfileRepository
from jobhunter.main import app

pytestmark = pytest.mark.integration


async def _seed(session: AsyncSession) -> tuple[uuid.UUID, list[uuid.UUID]]:
    profile = UserProfile(
        id=uuid.uuid4(),
        full_name="API Test User",
        email="api-test@example.com",
        headline="Engineer",
        location="Remote",
        remote_preference=RemotePolicy.REMOTE.value,
        salary_min=80000.0,
    )
    session.add(profile)
    await session.flush()

    skill = Skill(id=uuid.uuid4(), profile_id=profile.id, name="Python", proficiency="Expert")
    session.add(skill)

    exp = WorkExperience(
        id=uuid.uuid4(),
        profile_id=profile.id,
        company_name="Prev",
        title="Dev",
        start_date=date(2020, 1, 1),
        is_current=True,
    )
    session.add(exp)

    company = Company(id=uuid.uuid4(), name="APICorp", is_blacklisted=False)
    session.add(company)
    await session.flush()

    job = Job(
        id=uuid.uuid4(),
        source=JobSource.GREENHOUSE.value,
        external_id="api-score-001",
        url="https://example.com/api-score",
        title="Remote Python Dev",
        company_id=company.id,
        company_name="APICorp",
        remote_policy=RemotePolicy.REMOTE.value,
        salary_min=100000.0,
        salary_max=150000.0,
        description_raw="Python developer needed.",
        fetched_at=datetime.now(UTC),
    )
    session.add(job)
    await session.flush()
    await session.commit()
    return profile.id, [job.id]


@pytest.fixture(autouse=True)
def _override_deps(async_session: AsyncSession) -> Generator[None, Any]:
    from tests.fakes.embedder import FakeEmbedder
    from tests.fakes.scorer import FakeJobScorer

    async def _session_override() -> AsyncGenerator[AsyncSession]:
        yield async_session

    def _service_override() -> JobScoringService:
        return JobScoringService(
            job_repo=SQLAlchemyJobRepository(async_session),
            match_score_repo=SQLAlchemyMatchScoreRepository(async_session),
            profile_repo=SQLAlchemyUserProfileRepository(async_session),
            embedder=FakeEmbedder(),
            scorer=FakeJobScorer(),
            prefilter=PreFilter(),
            weight_config=WeightConfig(),
            session=async_session,
            threshold=0.5,
        )

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[_get_scoring_service] = _service_override
    yield
    app.dependency_overrides.clear()


class TestScoringEndpoints:
    async def test_score_and_list_matches(self, async_session: AsyncSession) -> None:
        profile_id, _ = await _seed(async_session)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/profiles/{profile_id}/score?limit=10")
            assert resp.status_code == 200
            body = resp.json()
            assert body["scored"] == 1
            assert body["prefiltered_out"] == 0

            resp2 = await client.get(f"/profiles/{profile_id}/matches?threshold=0.0")
            assert resp2.status_code == 200
            matches = resp2.json()
            assert len(matches) >= 1
            assert matches[0]["overall"] > 0.0

    async def test_score_missing_profile_returns_404(self) -> None:
        fake_id = uuid.uuid4()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/profiles/{fake_id}/score")
            assert resp.status_code == 404
