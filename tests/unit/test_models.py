"""Unit tests for ORM model registration (no DB required)."""

from jobhunter.infrastructure.db import models  # noqa: F401
from jobhunter.infrastructure.db.base import Base

EXPECTED_TABLES = {
    "companies",
    "user_profiles",
    "work_experiences",
    "educations",
    "projects",
    "certifications",
    "skills",
    "jobs",
    "match_scores",
    "resume_versions",
    "cover_letter_versions",
    "ats_reports",
    "applications",
    "application_answers",
    "screenshots",
    "notifications",
    "feedback_events",
}


def test_all_tables_registered_on_base() -> None:
    registered = set(Base.metadata.tables.keys())
    missing = EXPECTED_TABLES - registered
    assert not missing, f"Missing table registrations: {missing}"


def test_company_has_unique_name_index() -> None:
    table = Base.metadata.tables["companies"]
    index_names = {idx.name for idx in table.indexes}
    assert "ix_companies_name" in index_names


def test_jobs_unique_constraint() -> None:
    table = Base.metadata.tables["jobs"]
    constraint_names = {c.name for c in table.constraints if c.name}
    assert "uq_jobs_source_external_id" in constraint_names


def test_applications_unique_constraint() -> None:
    table = Base.metadata.tables["applications"]
    constraint_names = {c.name for c in table.constraints if c.name}
    assert "uq_applications_job_profile" in constraint_names
