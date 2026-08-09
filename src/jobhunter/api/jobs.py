"""Jobs API router — discovery trigger and basic CRUD."""

from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.adapters.boards.greenhouse import GreenhouseConnector
from jobhunter.adapters.boards.lever import LeverConnector
from jobhunter.adapters.boards.remoteok import RemoteOkConnector
from jobhunter.application.ports.job_source import JobSourceConnector
from jobhunter.application.use_cases.job_discovery import JobDiscoveryService
from jobhunter.domain.enums import JobSource
from jobhunter.domain.job_search import DiscoveryReport, JobSearchQuery
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


class DiscoverRequest(BaseModel):
    query: JobSearchQuery
    sources: list[JobSource] | None = None


def _get_discovery_service(session: AsyncSession = Depends(get_session)) -> JobDiscoveryService:  # noqa: B008
    client = httpx.AsyncClient(timeout=30.0)
    connectors: list[JobSourceConnector] = [
        GreenhouseConnector(client),
        LeverConnector(client),
        RemoteOkConnector(client),
    ]
    job_repo = SQLAlchemyJobRepository(session)
    company_repo = SQLAlchemyCompanyRepository(session)
    return JobDiscoveryService(
        connectors=connectors,
        job_repo=job_repo,
        company_repo=company_repo,
        session=session,
    )


@router.post("/discover")
async def discover_jobs(
    body: DiscoverRequest,
    service: JobDiscoveryService = Depends(_get_discovery_service),  # noqa: B008
) -> DiscoveryReport:
    return await service.discover(body.query, body.sources)


@router.get("")
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[dict[str, object]]:
    repo = SQLAlchemyJobRepository(session)
    jobs = await repo.list(limit=min(limit, 200), offset=offset)
    return [_serialize_job(j) for j in jobs]


@router.get("/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyJobRepository(session)
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


def _serialize_job(job: object) -> dict[str, object]:
    from jobhunter.infrastructure.db.models import Job

    j: Job = job  # type: ignore[assignment]
    return {
        "id": str(j.id),
        "source": j.source,
        "external_id": j.external_id,
        "url": j.url,
        "title": j.title,
        "company_name": j.company_name,
        "location": j.location,
        "remote_policy": j.remote_policy,
        "employment_type": j.employment_type,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "salary_currency": j.salary_currency,
        "description_raw": j.description_raw[:500] if j.description_raw else None,
        "posted_at": j.posted_at.isoformat() if j.posted_at else None,
        "fetched_at": j.fetched_at.isoformat() if j.fetched_at else None,
    }
