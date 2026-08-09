"""Job discovery use case — fetch from connectors, dedup, persist."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.exc import IntegrityError

from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import (
    DiscoveryReport,
    JobSearchQuery,
    RawJobPosting,
    SourceCounts,
)
from jobhunter.infrastructure.db.models import Job

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.application.ports.job_source import JobSourceConnector
    from jobhunter.application.repositories.company import CompanyRepository
    from jobhunter.application.repositories.job import JobRepository

logger = structlog.get_logger()


def _is_english(text: str) -> bool:
    """Return True if text is primarily English/ASCII characters.

    Counts the ratio of ASCII letters to total alphabetic characters.
    Jobs with mostly non-Latin scripts (Chinese, Arabic, etc.) return False.
    """
    if not text:
        return True  # empty text: don't filter out
    # Count ASCII letters vs total alphabetic characters
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters == 0:
        return True  # no letters at all (numbers/symbols): keep
    ratio = ascii_letters / total_letters
    return ratio >= 0.7  # at least 70% ASCII letters = treat as English


@dataclass
class _Accumulator:
    """Mutable per-source tallies used during processing."""

    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    errors: int = 0
    new_ids: list[uuid.UUID] = field(default_factory=list)

    def to_source_counts(self) -> SourceCounts:
        return SourceCounts(
            fetched=self.fetched,
            new=self.new,
            duplicates=self.duplicates,
            errors=self.errors,
        )


class JobDiscoveryService:
    """Orchestrates fetching, deduplication, and persistence of job postings."""

    def __init__(
        self,
        connectors: list[JobSourceConnector],
        job_repo: JobRepository,
        company_repo: CompanyRepository,
        session: AsyncSession,
    ) -> None:
        self._connectors = {c.source: c for c in connectors}
        self._job_repo = job_repo
        self._company_repo = company_repo
        self._session = session

    async def discover(
        self,
        query: JobSearchQuery,
        sources: list[JobSource] | None = None,
    ) -> DiscoveryReport:
        all_new_ids: list[uuid.UUID] = []
        per_source: dict[str, SourceCounts] = {}
        selected = sources or list(self._connectors.keys())

        for source_tag in selected:
            connector = self._connectors.get(source_tag)
            if connector is None:
                continue
            acc = await self._process_source(connector, query)
            per_source[source_tag.value] = acc.to_source_counts()
            all_new_ids.extend(acc.new_ids)

        return DiscoveryReport(new_job_ids=all_new_ids, per_source=per_source)

    async def _process_source(
        self, connector: JobSourceConnector, query: JobSearchQuery
    ) -> _Accumulator:
        acc = _Accumulator()
        try:
            postings = await connector.fetch(query)
        except Exception:
            logger.exception("connector_fetch_failed", source=connector.source.value)
            acc.errors = 1
            return acc

        acc.fetched = len(postings)
        for posting in postings:
            try:
                await self._process_posting(posting, acc)
            except Exception:
                logger.warning(
                    "posting_process_error",
                    source=posting.source.value,
                    external_id=posting.external_id,
                )
                acc.errors += 1

        await self._session.commit()
        return acc

    async def _process_posting(self, posting: RawJobPosting, acc: _Accumulator) -> None:
        # Skip non-English job postings
        if not _is_english(posting.title):
            logger.info(
                "skipped_non_english",
                source=posting.source.value,
                external_id=posting.external_id,
            )
            return  # do not insert

        exists = await self._job_repo.exists_by_source_external(
            posting.source.value, posting.external_id
        )
        if exists:
            acc.duplicates += 1
            return

        company = await self._company_repo.upsert_by_name(posting.company_name)

        job = Job(
            source=posting.source.value,
            external_id=posting.external_id,
            url=posting.url,
            title=posting.title,
            company_id=company.id,
            company_name=posting.company_name,
            location=posting.location,
            remote_policy=posting.remote_policy.value if posting.remote_policy else None,
            employment_type=posting.employment_type.value if posting.employment_type else None,
            salary_min=posting.salary_min,
            salary_max=posting.salary_max,
            salary_currency=posting.salary_currency,
            description_raw=posting.description_raw,
            posted_at=posting.posted_at,
            fetched_at=datetime.now(UTC),
        )

        # Savepoint per insert: if the unique constraint fires, only this
        # savepoint rolls back — the surrounding transaction stays usable.
        try:
            async with self._session.begin_nested():
                self._session.add(job)
                await self._session.flush()
            acc.new += 1
            acc.new_ids.append(job.id)
        except IntegrityError:
            acc.duplicates += 1
            logger.info(
                "dedup_integrity_backstop",
                source=posting.source.value,
                external_id=posting.external_id,
            )
