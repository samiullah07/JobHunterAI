"""Indeed connector — DEFERRED.

Per browser-automation-hitl policy: prefer official APIs over scraping gated sites.
Indeed's public search is gated behind bot-detection and CAPTCHAs. Their Partner API
requires a commercial agreement. This connector is deferred until ToS-compliant
access is secured.
"""

from __future__ import annotations

import httpx

from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting


class IndeedConnector:
    """Stub — raises NotImplementedError until ToS-compliant access is arranged."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def source(self) -> JobSource:
        return JobSource.INDEED

    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        raise NotImplementedError(
            "Indeed requires a Partner API agreement or HITL browser automation. "
            "Deferred until ToS-compliant access is secured."
        )
