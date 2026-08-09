"""Glassdoor connector — DEFERRED.

Per browser-automation-hitl policy: prefer official APIs over scraping gated sites.
Glassdoor's job listings are behind authentication and aggressive bot detection.
Their API program has been discontinued for new partners. Deferred until a
ToS-compliant path is available.
"""

from __future__ import annotations

import httpx

from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting


class GlassdoorConnector:
    """Stub — raises NotImplementedError. Glassdoor API program is closed."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def source(self) -> JobSource:
        return JobSource.GLASSDOOR

    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        raise NotImplementedError(
            "Glassdoor API program is discontinued for new partners. No ToS-compliant "
            "automated access path currently available. Deferred."
        )
