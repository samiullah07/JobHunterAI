"""Greenhouse public board API connector.

Public API (no auth): GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from jobhunter.adapters.boards import is_transient_http_error
from jobhunter.domain.enums import JobSource, RemotePolicy
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting

logger = structlog.get_logger()


class GreenhouseConnector:
    """Fetches jobs from Greenhouse public board API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def source(self) -> JobSource:
        return JobSource.GREENHOUSE

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception(is_transient_http_error),
        reraise=True,
    )
    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        if not query.board_token:
            return []
        url = f"https://boards-api.greenhouse.io/v1/boards/{query.board_token}/jobs"
        resp = await self._client.get(url, params={"content": "true"})
        resp.raise_for_status()
        data = resp.json()
        jobs_raw: list[dict[str, Any]] = data.get("jobs", [])
        results: list[RawJobPosting] = []
        for item in jobs_raw[: query.limit]:
            try:
                results.append(self._normalize(item, query.board_token))
            except Exception:
                logger.warning("greenhouse_parse_error", item_id=item.get("id"))
        return results

    def _normalize(self, item: dict[str, Any], board_token: str) -> RawJobPosting:
        location_name = ""
        if item.get("location") and item["location"].get("name"):
            location_name = item["location"]["name"]

        remote_policy = None
        if location_name and "remote" in location_name.lower():
            remote_policy = RemotePolicy.REMOTE

        job_id = str(item["id"])
        return RawJobPosting(
            source=JobSource.GREENHOUSE,
            external_id=job_id,
            url=f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}",
            title=item["title"],
            company_name=item.get("company", {}).get("name", board_token),
            location=location_name or None,
            remote_policy=remote_policy,
            employment_type=None,
            description_raw=item.get("content", ""),
            posted_at=None,
            raw=item,
        )
