"""RemoteOK public job feed connector.

Public feed (no auth): GET https://remoteok.com/api
First element in the response is metadata (not a job posting) — skip it.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from jobhunter.adapters.boards import is_transient_http_error
from jobhunter.domain.enums import EmploymentType, JobSource, RemotePolicy
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting

logger = structlog.get_logger()


class RemoteOkConnector:
    """Fetches jobs from the RemoteOK public JSON feed."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def source(self) -> JobSource:
        return JobSource.REMOTEOK

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception(is_transient_http_error),
        reraise=True,
    )
    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        url = "https://remoteok.com/api"
        params: dict[str, str] = {}
        if query.keywords:
            params["tag"] = query.keywords
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()
        results: list[RawJobPosting] = []
        for item in data[: query.limit + 1]:
            if not item.get("id"):
                continue
            try:
                results.append(self._normalize(item))
            except Exception:
                logger.warning("remoteok_parse_error", item_id=item.get("id"))
            if len(results) >= query.limit:
                break
        return results

    def _normalize(self, item: dict[str, Any]) -> RawJobPosting:
        posted_at = None
        if item.get("date"):
            with contextlib.suppress(ValueError, TypeError):
                posted_at = datetime.fromisoformat(item["date"]).replace(tzinfo=UTC)

        salary_min = None
        salary_max = None
        if item.get("salary_min"):
            with contextlib.suppress(ValueError, TypeError):
                salary_min = float(item["salary_min"])
        if item.get("salary_max"):
            with contextlib.suppress(ValueError, TypeError):
                salary_max = float(item["salary_max"])

        return RawJobPosting(
            source=JobSource.REMOTEOK,
            external_id=str(item["id"]),
            url=item.get("url", f"https://remoteok.com/l/{item['id']}"),
            title=item.get("position", "Unknown"),
            company_name=item.get("company", "Unknown"),
            location=item.get("location") or None,
            remote_policy=RemotePolicy.REMOTE,
            employment_type=EmploymentType.FULL_TIME
            if not item.get("contract")
            else EmploymentType.CONTRACT,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if (salary_min or salary_max) else None,
            description_raw=item.get("description", ""),
            posted_at=posted_at,
            raw=item,
        )
