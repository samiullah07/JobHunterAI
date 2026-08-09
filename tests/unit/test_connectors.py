"""Unit tests for job source connectors — all offline via httpx.MockTransport."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from jobhunter.adapters.boards.glassdoor import GlassdoorConnector
from jobhunter.adapters.boards.greenhouse import GreenhouseConnector
from jobhunter.adapters.boards.indeed import IndeedConnector
from jobhunter.adapters.boards.lever import LeverConnector
from jobhunter.adapters.boards.linkedin import LinkedInConnector
from jobhunter.adapters.boards.remoteok import RemoteOkConnector
from jobhunter.domain.enums import EmploymentType, JobSource, RemotePolicy
from jobhunter.domain.job_search import JobSearchQuery

FIXTURES = Path(__file__).parent.parent / "fixtures" / "boards"


def _mock_client(fixture_file: str) -> httpx.AsyncClient:
    data = (FIXTURES / fixture_file).read_text()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json.loads(data))

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestGreenhouseConnector:
    async def test_fetches_and_normalizes(self) -> None:
        client = _mock_client("greenhouse.json")
        connector = GreenhouseConnector(client)
        query = JobSearchQuery(board_token="acme")
        results = await connector.fetch(query)
        assert len(results) == 2
        assert results[0].source == JobSource.GREENHOUSE
        assert results[0].external_id == "4012345"
        assert results[0].title == "Senior Backend Engineer"
        assert results[0].company_name == "Acme Corp"
        assert results[0].location == "San Francisco, CA"
        assert results[0].remote_policy is None

    async def test_detects_remote(self) -> None:
        client = _mock_client("greenhouse.json")
        connector = GreenhouseConnector(client)
        query = JobSearchQuery(board_token="acme")
        results = await connector.fetch(query)
        assert results[1].remote_policy == RemotePolicy.REMOTE
        assert "Remote" in (results[1].location or "")

    async def test_skips_malformed_posting(self) -> None:
        client = _mock_client("greenhouse.json")
        connector = GreenhouseConnector(client)
        query = JobSearchQuery(board_token="acme")
        results = await connector.fetch(query)
        assert len(results) == 2

    async def test_returns_empty_without_board_token(self) -> None:
        client = _mock_client("greenhouse.json")
        connector = GreenhouseConnector(client)
        query = JobSearchQuery()
        results = await connector.fetch(query)
        assert results == []

    async def test_source_property(self) -> None:
        client = _mock_client("greenhouse.json")
        connector = GreenhouseConnector(client)
        assert connector.source == JobSource.GREENHOUSE


class TestLeverConnector:
    async def test_fetches_and_normalizes(self) -> None:
        client = _mock_client("lever.json")
        connector = LeverConnector(client)
        query = JobSearchQuery(board_token="example")
        results = await connector.fetch(query)
        assert len(results) == 2
        assert results[0].source == JobSource.LEVER
        assert results[0].external_id == "abc-def-123"
        assert results[0].title == "Staff Engineer, Platform"
        assert results[0].company_name == "ExampleCo"
        assert results[0].employment_type == EmploymentType.FULL_TIME

    async def test_detects_remote_and_contract(self) -> None:
        client = _mock_client("lever.json")
        connector = LeverConnector(client)
        query = JobSearchQuery(board_token="example")
        results = await connector.fetch(query)
        assert results[1].remote_policy == RemotePolicy.REMOTE
        assert results[1].employment_type == EmploymentType.CONTRACT

    async def test_skips_malformed_entry(self) -> None:
        client = _mock_client("lever.json")
        connector = LeverConnector(client)
        query = JobSearchQuery(board_token="example")
        results = await connector.fetch(query)
        assert len(results) == 2

    async def test_source_property(self) -> None:
        client = _mock_client("lever.json")
        connector = LeverConnector(client)
        assert connector.source == JobSource.LEVER


class TestRemoteOkConnector:
    async def test_fetches_and_normalizes(self) -> None:
        client = _mock_client("remoteok.json")
        connector = RemoteOkConnector(client)
        query = JobSearchQuery(keywords="python")
        results = await connector.fetch(query)
        assert len(results) == 2
        assert results[0].source == JobSource.REMOTEOK
        assert results[0].external_id == "101001"
        assert results[0].title == "Python Developer"
        assert results[0].company_name == "RemoteTech"
        assert results[0].remote_policy == RemotePolicy.REMOTE
        assert results[0].salary_min == 80000.0
        assert results[0].salary_max == 120000.0
        assert results[0].salary_currency == "USD"

    async def test_skips_metadata_and_empty_id(self) -> None:
        client = _mock_client("remoteok.json")
        connector = RemoteOkConnector(client)
        query = JobSearchQuery()
        results = await connector.fetch(query)
        assert len(results) == 2
        assert all(r.external_id for r in results)

    async def test_posted_at_parsed(self) -> None:
        client = _mock_client("remoteok.json")
        connector = RemoteOkConnector(client)
        query = JobSearchQuery()
        results = await connector.fetch(query)
        assert results[0].posted_at is not None

    async def test_source_property(self) -> None:
        client = _mock_client("remoteok.json")
        connector = RemoteOkConnector(client)
        assert connector.source == JobSource.REMOTEOK


class TestConnectorErrorHandling:
    """4xx responses raise immediately (not retried); distinguishable from empty board."""

    async def test_greenhouse_404_raises(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "not found"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        connector = GreenhouseConnector(client)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await connector.fetch(JobSearchQuery(board_token="nonexistent"))
        assert exc_info.value.response.status_code == 404

    async def test_lever_404_raises(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "not found"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        connector = LeverConnector(client)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await connector.fetch(JobSearchQuery(board_token="nonexistent"))
        assert exc_info.value.response.status_code == 404

    async def test_remoteok_404_raises(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="not found")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        connector = RemoteOkConnector(client)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await connector.fetch(JobSearchQuery(keywords="python"))
        assert exc_info.value.response.status_code == 404

    async def test_greenhouse_500_is_retried_then_raises(self) -> None:
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, json={"error": "server error"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        connector = GreenhouseConnector(client)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await connector.fetch(JobSearchQuery(board_token="flaky"))
        assert exc_info.value.response.status_code == 500
        assert call_count == 3  # 1 initial + 2 retries (stop_after_attempt(3))


class TestDeferredConnectors:
    async def test_linkedin_raises(self) -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
        connector = LinkedInConnector(client)
        with pytest.raises(NotImplementedError, match="LinkedIn"):
            await connector.fetch(JobSearchQuery())

    async def test_indeed_raises(self) -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
        connector = IndeedConnector(client)
        with pytest.raises(NotImplementedError, match="Indeed"):
            await connector.fetch(JobSearchQuery())

    async def test_glassdoor_raises(self) -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
        connector = GlassdoorConnector(client)
        with pytest.raises(NotImplementedError, match="Glassdoor"):
            await connector.fetch(JobSearchQuery())
