"""Integration tests for JobDiscoveryService — real DB on port 5433."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.application.use_cases.job_discovery import JobDiscoveryService
from jobhunter.domain.enums import JobSource, RemotePolicy
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting
from jobhunter.infrastructure.db.models import Job
from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository

pytestmark = pytest.mark.integration


def _make_postings() -> list[RawJobPosting]:
    return [
        RawJobPosting(
            source=JobSource.GREENHOUSE,
            external_id="gh-001",
            url="https://boards.greenhouse.io/acme/jobs/001",
            title="Backend Engineer",
            company_name="Acme Corp",
            location="NYC",
            remote_policy=RemotePolicy.HYBRID,
            description_raw="Build APIs.",
        ),
        RawJobPosting(
            source=JobSource.GREENHOUSE,
            external_id="gh-002",
            url="https://boards.greenhouse.io/acme/jobs/002",
            title="Frontend Engineer",
            company_name="Acme Corp",
            location="Remote",
            remote_policy=RemotePolicy.REMOTE,
            description_raw="Build UIs.",
        ),
        RawJobPosting(
            source=JobSource.GREENHOUSE,
            external_id="gh-003",
            url="https://boards.greenhouse.io/beta/jobs/003",
            title="Data Scientist",
            company_name="Beta Labs",
            description_raw="Analyze data.",
        ),
    ]


class FakeConnector:
    """In-memory connector for testing."""

    def __init__(self, postings: list[RawJobPosting]) -> None:
        self._postings = postings

    @property
    def source(self) -> JobSource:
        return JobSource.GREENHOUSE

    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        return self._postings


class TestDiscoverNewJobs:
    async def test_persists_new_jobs_and_companies(self, async_session: AsyncSession) -> None:
        job_repo = SQLAlchemyJobRepository(async_session)
        company_repo = SQLAlchemyCompanyRepository(async_session)
        connector = FakeConnector(_make_postings())
        service = JobDiscoveryService(
            connectors=[connector],
            job_repo=job_repo,
            company_repo=company_repo,
            session=async_session,
        )

        report = await service.discover(JobSearchQuery())
        counts = report.per_source["greenhouse"]
        assert counts.fetched == 3
        assert counts.new == 3
        assert counts.duplicates == 0
        assert counts.errors == 0
        assert len(report.new_job_ids) == 3

        acme = await company_repo.get_by_name("Acme Corp")
        assert acme is not None
        beta = await company_repo.get_by_name("Beta Labs")
        assert beta is not None

        jobs = await job_repo.list(limit=10)
        assert len(jobs) == 3


class TestDeduplication:
    async def test_second_run_all_duplicates(self, async_session: AsyncSession) -> None:
        job_repo = SQLAlchemyJobRepository(async_session)
        company_repo = SQLAlchemyCompanyRepository(async_session)
        connector = FakeConnector(_make_postings())
        service = JobDiscoveryService(
            connectors=[connector],
            job_repo=job_repo,
            company_repo=company_repo,
            session=async_session,
        )

        await service.discover(JobSearchQuery())
        report2 = await service.discover(JobSearchQuery())
        counts = report2.per_source["greenhouse"]
        assert counts.fetched == 3
        assert counts.new == 0
        assert counts.duplicates == 3

    async def test_integrity_error_backstop(self, async_session: AsyncSession) -> None:
        """A posting that slips past exists-check hits the unique constraint backstop."""
        company_repo = SQLAlchemyCompanyRepository(async_session)

        company = await company_repo.upsert_by_name("PreExisting")
        pre_existing = Job(
            source=JobSource.GREENHOUSE.value,
            external_id="gh-sneaky",
            url="https://example.com/sneaky",
            title="Sneaky Job",
            company_id=company.id,
            company_name="PreExisting",
            description_raw="Already here.",
            fetched_at=datetime.now(UTC),
        )
        async with async_session.begin_nested():
            async_session.add(pre_existing)
            await async_session.flush()

        posting = RawJobPosting(
            source=JobSource.GREENHOUSE,
            external_id="gh-sneaky",
            url="https://example.com/sneaky",
            title="Sneaky Job",
            company_name="PreExisting",
            description_raw="Already here.",
        )

        class SneakyConnector:
            @property
            def source(self) -> JobSource:
                return JobSource.GREENHOUSE

            async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
                return [posting]

        class SneakyJobRepo(SQLAlchemyJobRepository):
            async def exists_by_source_external(self, source: str, external_id: str) -> bool:
                return False

        sneaky_repo = SneakyJobRepo(async_session)
        service = JobDiscoveryService(
            connectors=[SneakyConnector()],
            job_repo=sneaky_repo,
            company_repo=company_repo,
            session=async_session,
        )

        report = await service.discover(JobSearchQuery())
        counts = report.per_source["greenhouse"]
        assert counts.duplicates == 1
        assert counts.new == 0

    async def test_integrityerror_backstop_batch_continues(
        self, async_session: AsyncSession
    ) -> None:
        """After a backstop collision, subsequent inserts in the same batch still persist.

        This proves the savepoint-per-insert pattern works: the IntegrityError rolls
        back only its savepoint, not the whole transaction.
        """
        job_repo = SQLAlchemyJobRepository(async_session)
        company_repo = SQLAlchemyCompanyRepository(async_session)

        # Pre-insert a job that will collide with the second posting in the batch.
        company = await company_repo.upsert_by_name("Collider Inc")
        colliding_job = Job(
            source=JobSource.GREENHOUSE.value,
            external_id="gh-collide",
            url="https://example.com/collide",
            title="Collider",
            company_id=company.id,
            company_name="Collider Inc",
            description_raw="Pre-existing.",
            fetched_at=datetime.now(UTC),
        )
        async with async_session.begin_nested():
            async_session.add(colliding_job)
            await async_session.flush()

        # Batch: [new-before, collision, new-after].
        # The exists-check will always return False (SneakyJobRepo), forcing the
        # collision to hit the DB unique constraint.
        batch = [
            RawJobPosting(
                source=JobSource.GREENHOUSE,
                external_id="gh-before",
                url="https://example.com/before",
                title="Before Collision",
                company_name="Collider Inc",
                description_raw="I come first.",
            ),
            RawJobPosting(
                source=JobSource.GREENHOUSE,
                external_id="gh-collide",
                url="https://example.com/collide",
                title="Collider",
                company_name="Collider Inc",
                description_raw="I will collide.",
            ),
            RawJobPosting(
                source=JobSource.GREENHOUSE,
                external_id="gh-after",
                url="https://example.com/after",
                title="After Collision",
                company_name="Collider Inc",
                description_raw="I come after.",
            ),
        ]

        class BatchConnector:
            @property
            def source(self) -> JobSource:
                return JobSource.GREENHOUSE

            async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
                return batch

        class AlwaysMissRepo(SQLAlchemyJobRepository):
            async def exists_by_source_external(self, source: str, external_id: str) -> bool:
                return False

        service = JobDiscoveryService(
            connectors=[BatchConnector()],
            job_repo=AlwaysMissRepo(async_session),
            company_repo=company_repo,
            session=async_session,
        )

        report = await service.discover(JobSearchQuery())
        counts = report.per_source["greenhouse"]

        # The collision is caught; the other two succeed.
        assert counts.fetched == 3
        assert counts.new == 2
        assert counts.duplicates == 1
        assert counts.errors == 0
        assert len(report.new_job_ids) == 2

        # Verify both non-colliding jobs are actually persisted.
        before = await job_repo.get_by_source_external(JobSource.GREENHOUSE.value, "gh-before")
        after = await job_repo.get_by_source_external(JobSource.GREENHOUSE.value, "gh-after")
        assert before is not None
        assert after is not None

    async def test_duplicate_in_same_batch(self, async_session: AsyncSession) -> None:
        """Same (source, external_id) twice in one batch: first inserts, second is backstopped."""
        job_repo = SQLAlchemyJobRepository(async_session)
        company_repo = SQLAlchemyCompanyRepository(async_session)

        duplicate_posting = RawJobPosting(
            source=JobSource.GREENHOUSE,
            external_id="gh-dup",
            url="https://example.com/dup",
            title="Duplicate Job",
            company_name="DupCorp",
            description_raw="Appears twice.",
        )
        batch = [duplicate_posting, duplicate_posting]

        class DupConnector:
            @property
            def source(self) -> JobSource:
                return JobSource.GREENHOUSE

            async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
                return batch

        service = JobDiscoveryService(
            connectors=[DupConnector()],
            job_repo=job_repo,
            company_repo=company_repo,
            session=async_session,
        )

        report = await service.discover(JobSearchQuery())
        counts = report.per_source["greenhouse"]
        # First insert succeeds; second hits exists-check (or backstop).
        # Since both have the same external_id and the exists-check queries
        # the DB, the second will find the first (flushed via savepoint) and
        # count as a duplicate via the fast path.
        assert counts.fetched == 2
        assert counts.new == 1
        assert counts.duplicates == 1
        assert len(report.new_job_ids) == 1
