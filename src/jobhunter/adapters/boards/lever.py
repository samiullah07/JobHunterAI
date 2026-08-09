"""Lever public postings API connector.

Public API (no auth): GET https://api.lever.co/v0/postings/{board_token}?mode=json
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from jobhunter.adapters.boards import is_transient_http_error
from jobhunter.domain.enums import EmploymentType, JobSource, RemotePolicy
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting

logger = structlog.get_logger()


_COMMITMENT_MAP: dict[str, EmploymentType] = {
    "Full-time": EmploymentType.FULL_TIME,
    "Part-time": EmploymentType.PART_TIME,
    "Contract": EmploymentType.CONTRACT,
    "Intern": EmploymentType.INTERNSHIP,
    "Temporary": EmploymentType.TEMPORARY,
}


class LeverConnector:
    """Fetches jobs from Lever public postings API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def source(self) -> JobSource:
        return JobSource.LEVER

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception(is_transient_http_error),
        reraise=True,
    )
    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        if not query.board_token:
            return []
        url = f"https://api.lever.co/v0/postings/{query.board_token}"
        resp = await self._client.get(url, params={"mode": "json"})
        resp.raise_for_status()
        postings: list[dict[str, Any]] = resp.json()
        results: list[RawJobPosting] = []
        for item in postings[: query.limit]:
            try:
                results.append(self._normalize(item))
            except Exception:
                logger.warning("lever_parse_error", item_id=item.get("id"))
        return results

    def _normalize(self, item: dict[str, Any]) -> RawJobPosting:
        categories = item.get("categories", {})
        location_str = categories.get("location", None)
        commitment = categories.get("commitment", "")

        remote_policy = None
        if location_str and "remote" in location_str.lower():
            remote_policy = RemotePolicy.REMOTE

        employment_type = _COMMITMENT_MAP.get(commitment)

        description = item.get("descriptionPlain", "") or item.get("description", "")

        return RawJobPosting(
            source=JobSource.LEVER,
            external_id=item["id"],
            url=item.get("hostedUrl", "") or item.get("applyUrl", ""),
            title=item["text"],
            company_name=item.get("company", "Unknown"),
            location=location_str,
            remote_policy=remote_policy,
            employment_type=employment_type,
            description_raw=description,
            posted_at=None,
            raw=item,
        )
