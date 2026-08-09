"""Integration test: verify all ORM tables are created correctly in a real Postgres."""

import shutil
import subprocess

import pytest
from sqlalchemy import create_engine, inspect, text

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


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.mark.integration
def test_all_tables_created() -> None:
    if not _docker_available():
        pytest.skip("Docker not available — cannot run integration test")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg2") as pg:
        url = pg.get_connection_url()
        engine = create_engine(url)

        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        from jobhunter.infrastructure.db import models  # noqa: F401
        from jobhunter.infrastructure.db.base import Base

        Base.metadata.create_all(engine)

        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())

        missing = EXPECTED_TABLES - actual_tables
        assert not missing, f"Missing tables: {missing}"
