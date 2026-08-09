"""Pure domain DTOs for job search and discovery."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from jobhunter.domain.enums import EmploymentType, JobSource, RemotePolicy


class JobSearchQuery(BaseModel):
    """Parameters for a job search across one or more sources."""

    model_config = ConfigDict(strict=True)

    keywords: str | None = None
    location: str | None = None
    remote: RemotePolicy | None = None
    employment_type: EmploymentType | None = None
    company: str | None = None
    board_token: str | None = None
    limit: int = 50


class RawJobPosting(BaseModel):
    """Normalized job posting from a connector — not yet persisted."""

    model_config = ConfigDict(strict=True)

    source: JobSource
    external_id: str
    url: str
    title: str
    company_name: str
    location: str | None = None
    remote_policy: RemotePolicy | None = None
    employment_type: EmploymentType | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    description_raw: str
    posted_at: datetime | None = None
    raw: dict[str, Any] = {}


class DiscoveryReport(BaseModel):
    """Result of a discovery run — per-source counts."""

    model_config = ConfigDict(strict=True)

    new_job_ids: list[uuid.UUID] = []
    per_source: dict[str, SourceCounts] = {}


class SourceCounts(BaseModel):
    model_config = ConfigDict(strict=True)

    fetched: int = 0
    new: int = 0
    duplicates: int = 0
    errors: int = 0
