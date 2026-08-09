"""API tests for /jobs endpoints — all offline, connector dependency overridden."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.api.jobs import _get_discovery_service
from jobhunter.application.use_cases.job_discovery import JobDiscoveryService
from jobhunter.domain.enums import JobSource, RemotePolicy
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.main import app

pytestmark = pytest.mark.integration


class FakeConnector:
    @property
    def source(self) -> JobSource:
        return JobSource.GREENHOUSE

    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        return [
            RawJobPosting(
                source=JobSource.GREENHOUSE,
                external_id="api-test-001",
                url="https://example.com/jobs/001",
                title="API Test Engineer",
                company_name="TestCorp",
                location="Remote",
                remote_policy=RemotePolicy.REMOTE,
                description_raw="Test job for API.",
            ),
            RawJobPosting(
                source=JobSource.GREENHOUSE,
                external_id="api-test-002",
                url="https://example.com/jobs/002",
                title="API Test Designer",
                company_name="TestCorp",
                description_raw="Design stuff.",
            ),
        ]


@pytest.fixture(autouse=True)
def _override_deps(async_session: AsyncSession) -> Generator[None, Any]:
    async def _session_override() -> AsyncGenerator[AsyncSession]:
        yield async_session

    def _service_override() -> JobDiscoveryService:
        job_repo = SQLAlchemyJobRepository(async_session)
        company_repo = SQLAlchemyCompanyRepository(async_session)
        return JobDiscoveryService(
            connectors=[FakeConnector()],
            job_repo=job_repo,
            company_repo=company_repo,
            session=async_session,
        )

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[_get_discovery_service] = _service_override
    yield
    app.dependency_overrides.clear()


class TestDiscoverEndpoint:
    async def test_discover_returns_report(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/jobs/discover",
                json={"query": {"board_token": "test"}},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "per_source" in body
            assert body["per_source"]["greenhouse"]["new"] == 2
            assert body["per_source"]["greenhouse"]["duplicates"] == 0
            assert len(body["new_job_ids"]) == 2


class TestJobsListAndGet:
    async def test_list_and_get_after_discover(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post("/jobs/discover", json={"query": {"board_token": "test"}})

            resp = await client.get("/jobs", params={"limit": 10})
            assert resp.status_code == 200
            jobs = resp.json()
            assert len(jobs) == 2

            job_id = jobs[0]["id"]
            resp2 = await client.get(f"/jobs/{job_id}")
            assert resp2.status_code == 200
            assert resp2.json()["id"] == job_id

    async def test_get_nonexistent_returns_404(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/jobs/00000000-0000-0000-0000-000000000000")
            assert resp.status_code == 404
