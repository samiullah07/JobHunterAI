"""LinkedIn connector — DEFERRED.

Per browser-automation-hitl policy: prefer official APIs over scraping gated sites.
LinkedIn requires authenticated sessions and prohibits automated scraping in its ToS.
This connector will be implemented in a later milestone using human-in-the-loop
browser automation with explicit session management and ToS-compliant rate limiting.
"""

from __future__ import annotations

import httpx

from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting


class LinkedInConnector:
    """Stub — raises NotImplementedError until HITL browser automation is ready."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @property
    def source(self) -> JobSource:
        return JobSource.LINKEDIN

    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]:
        raise NotImplementedError(
            "LinkedIn requires authenticated sessions and ToS-compliant HITL browser "
            "automation. Deferred to M8+ (browser-automation milestone)."
        )
