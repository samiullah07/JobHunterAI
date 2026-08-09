"""Integration test: round-trip insert + query with relationships against real Postgres."""

import shutil
import subprocess
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import configure_mappers, sessionmaker


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
def test_configure_mappers() -> None:
    """Validate all back_populates / relationship declarations."""
    from jobhunter.infrastructure.db import models  # noqa: F401

    configure_mappers()


@pytest.mark.integration
def test_roundtrip_user_profile_with_work_experience() -> None:
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
        from jobhunter.infrastructure.db.models import UserProfile, WorkExperience

        Base.metadata.create_all(engine)

        factory = sessionmaker(engine, expire_on_commit=False)

        profile_id = uuid.uuid4()
        exp_id = uuid.uuid4()

        with factory() as session:
            profile = UserProfile(
                id=profile_id,
                full_name="Test User",
                email="test@example.com",
            )
            exp = WorkExperience(
                id=exp_id,
                profile_id=profile_id,
                company_name="Acme Corp",
                title="Engineer",
                start_date=date(2020, 1, 1),
                is_current=True,
            )
            session.add(profile)
            session.add(exp)
            session.commit()

        with factory() as session:
            loaded = session.get(UserProfile, profile_id)
            assert loaded is not None
            assert loaded.full_name == "Test User"
            assert len(loaded.work_experiences) == 1
            assert loaded.work_experiences[0].company_name == "Acme Corp"
            assert loaded.work_experiences[0].is_current is True

            session.delete(loaded)
            session.commit()

        with factory() as session:
            assert session.get(UserProfile, profile_id) is None
            assert session.get(WorkExperience, exp_id) is None
