"""Job source connector port — interface for fetching postings from boards/feeds."""

from __future__ import annotations

from typing import Protocol

from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import JobSearchQuery, RawJobPosting


class JobSourceConnector(Protocol):
    @property
    def source(self) -> JobSource: ...

    async def fetch(self, query: JobSearchQuery) -> list[RawJobPosting]: ...
