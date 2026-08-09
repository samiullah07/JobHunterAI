"""Integration tests for repository implementations against real Postgres."""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.domain.enums import ApplicationStatus, JobSource
from jobhunter.infrastructure.db.models import (
    Application,
    ApplicationAnswer,
    Job,
    MatchScore,
    Screenshot,
    UserProfile,
    WorkExperience,
)
from jobhunter.infrastructure.repositories.application import (
    SQLAlchemyApplicationRepository,
)
from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.user_profile import (
    SQLAlchemyUserProfileRepository,
)


def _make_profile(profile_id: uuid.UUID | None = None) -> UserProfile:
    return UserProfile(
        id=profile_id or uuid.uuid4(),
        full_name="Jane Doe",
        email=f"jane-{uuid.uuid4().hex[:8]}@example.com",
    )


def _make_job(company_name: str = "Acme", source: str = JobSource.LINKEDIN) -> Job:
    return Job(
        id=uuid.uuid4(),
        source=source,
        external_id=uuid.uuid4().hex,
        url="https://example.com/job/1",
        title="Software Engineer",
        company_name=company_name,
        description_raw="Build things.",
        fetched_at=datetime.now(UTC),
    )


@pytest.mark.integration
class TestUserProfileRepository:
    async def test_add_and_get_with_children(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyUserProfileRepository(async_session)
        profile_id = uuid.uuid4()
        profile = _make_profile(profile_id)
        await repo.add(profile)

        exp = WorkExperience(
            id=uuid.uuid4(),
            profile_id=profile_id,
            company_name="TestCo",
            title="Dev",
            start_date=date(2021, 1, 1),
            is_current=True,
        )
        async_session.add(exp)
        await async_session.flush()

        loaded = await repo.get_with_children(profile_id)
        assert loaded is not None
        assert loaded.full_name == "Jane Doe"
        assert len(loaded.work_experiences) == 1
        assert loaded.work_experiences[0].company_name == "TestCo"

    async def test_get_by_email(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyUserProfileRepository(async_session)
        profile = _make_profile()
        await repo.add(profile)

        found = await repo.get_by_email(profile.email)
        assert found is not None
        assert found.id == profile.id

        not_found = await repo.get_by_email("nonexistent@example.com")
        assert not_found is None


@pytest.mark.integration
class TestCompanyRepository:
    async def test_upsert_by_name_idempotent(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyCompanyRepository(async_session)

        c1 = await repo.upsert_by_name("Acme Corp", website="https://acme.com")
        c2 = await repo.upsert_by_name("Acme Corp", website="https://acme.io")

        assert c1.id == c2.id
        assert c2.website == "https://acme.io"

    async def test_get_by_name(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyCompanyRepository(async_session)
        await repo.upsert_by_name("UniqueTestCo")

        found = await repo.get_by_name("UniqueTestCo")
        assert found is not None
        assert found.name == "UniqueTestCo"

        assert await repo.get_by_name("NoSuchCo") is None


@pytest.mark.integration
class TestJobRepository:
    async def test_get_by_source_external(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyJobRepository(async_session)
        job = _make_job()
        await repo.add(job)

        found = await repo.get_by_source_external(job.source, job.external_id)
        assert found is not None
        assert found.id == job.id

    async def test_exists_by_source_external(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyJobRepository(async_session)
        job = _make_job()
        await repo.add(job)

        assert await repo.exists_by_source_external(job.source, job.external_id) is True
        assert await repo.exists_by_source_external("indeed", "fake") is False

    async def test_list_unscored(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyJobRepository(async_session)
        profile = _make_profile()
        async_session.add(profile)
        await async_session.flush()

        job1 = _make_job()
        job2 = _make_job()
        await repo.add(job1)
        await repo.add(job2)

        score = MatchScore(
            id=uuid.uuid4(),
            job_id=job1.id,
            profile_id=profile.id,
            overall=0.9,
        )
        async_session.add(score)
        await async_session.flush()

        unscored = await repo.list_unscored(profile.id)
        unscored_ids = {j.id for j in unscored}
        assert job2.id in unscored_ids
        assert job1.id not in unscored_ids


@pytest.mark.integration
class TestApplicationRepository:
    async def test_unique_job_profile_constraint(self, async_session: AsyncSession) -> None:
        profile = _make_profile()
        async_session.add(profile)
        job = _make_job()
        async_session.add(job)
        await async_session.flush()

        app1 = Application(
            id=uuid.uuid4(),
            job_id=job.id,
            profile_id=profile.id,
            status=ApplicationStatus.SAVED,
        )
        async_session.add(app1)
        await async_session.flush()

        app2 = Application(
            id=uuid.uuid4(),
            job_id=job.id,
            profile_id=profile.id,
            status=ApplicationStatus.SAVED,
        )
        async_session.add(app2)
        with pytest.raises(IntegrityError):
            await async_session.flush()

    async def test_get_review_packet_eager_loads(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyApplicationRepository(async_session)
        profile = _make_profile()
        async_session.add(profile)
        job = _make_job()
        async_session.add(job)
        await async_session.flush()

        app = Application(
            id=uuid.uuid4(),
            job_id=job.id,
            profile_id=profile.id,
            status=ApplicationStatus.READY_FOR_REVIEW,
        )
        async_session.add(app)
        await async_session.flush()

        answer = ApplicationAnswer(
            id=uuid.uuid4(),
            application_id=app.id,
            question="Why this role?",
            value="I love building things.",
            source="profile_summary",
        )
        screenshot = Screenshot(
            id=uuid.uuid4(),
            application_id=app.id,
            step_label="form_page_1",
            storage_key="screenshots/abc.png",
            is_final=False,
        )
        async_session.add_all([answer, screenshot])
        await async_session.flush()

        loaded = await repo.get_review_packet(app.id)
        assert loaded is not None
        assert loaded.job.title == "Software Engineer"
        assert len(loaded.answers) == 1
        assert loaded.answers[0].question == "Why this role?"
        assert len(loaded.screenshots) == 1
        assert loaded.screenshots[0].step_label == "form_page_1"
