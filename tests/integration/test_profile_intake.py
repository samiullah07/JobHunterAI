"""Integration tests for ProfileIntakeService — real DB on port 5433."""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.application.use_cases.profile_intake import ProfileIntakeService
from jobhunter.domain.enums import EmploymentType, RemotePolicy
from jobhunter.domain.profile import (
    ParsedResume,
    ParsedSkill,
    ProfileInput,
    SkillInput,
    WorkExperienceInput,
)
from jobhunter.infrastructure.repositories.user_profile import (
    SQLAlchemyUserProfileRepository,
)

pytestmark = pytest.mark.integration


def _make_profile(email: str = "jane@example.com") -> ProfileInput:
    return ProfileInput(
        full_name="Jane Doe",
        email=email,
        headline="Senior Engineer",
        summary="Experienced developer.",
        remote_preference=RemotePolicy.REMOTE,
        employment_types=[EmploymentType.FULL_TIME],
        salary_min=100000,
        salary_max=150000,
        salary_currency="USD",
        work_experiences=[
            WorkExperienceInput(
                company_name="Acme Corp",
                title="Senior Engineer",
                start_date=date(2020, 1, 15),
                is_current=True,
                description="Built stuff.",
                achievements=["Shipped v2"],
                technologies=["Python"],
            )
        ],
        skills=[
            SkillInput(name="Python", category="Language", proficiency="Expert"),
            SkillInput(name="SQL", category="Database"),
        ],
    )


class TestCreateOrUpdateProfile:
    async def test_create_new_profile(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyUserProfileRepository(async_session)
        service = ProfileIntakeService(user_profile_repo=repo, session=async_session)
        data = _make_profile()
        profile_id = await service.create_or_update_profile(data)
        assert isinstance(profile_id, uuid.UUID)

        loaded = await repo.get_with_children(profile_id)
        assert loaded is not None
        assert loaded.full_name == "Jane Doe"
        assert loaded.email == "jane@example.com"
        assert len(loaded.work_experiences) == 1
        assert len(loaded.skills) == 2

    async def test_idempotent_by_email(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyUserProfileRepository(async_session)
        service = ProfileIntakeService(user_profile_repo=repo, session=async_session)
        data1 = _make_profile()
        id1 = await service.create_or_update_profile(data1)

        data2 = ProfileInput(
            full_name="Jane Smith",
            email="jane@example.com",
            headline="Staff Engineer",
            skills=[SkillInput(name="Go", category="Language")],
        )
        id2 = await service.create_or_update_profile(data2)

        assert id1 == id2
        loaded = await repo.get_with_children(id2)
        assert loaded is not None
        assert loaded.full_name == "Jane Smith"
        assert loaded.headline == "Staff Engineer"
        assert len(loaded.skills) == 1
        assert loaded.skills[0].name == "Go"


class TestAcceptParsedResume:
    async def test_overrides_win(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyUserProfileRepository(async_session)
        service = ProfileIntakeService(user_profile_repo=repo, session=async_session)

        parsed = ParsedResume(
            source_filename="resume.pdf",
            full_name="Parser Name",
            email="parsed@example.com",
            headline="Parsed Headline",
            confidence={"full_name": 0.9, "email": 0.95, "headline": 0.7},
            skills=[ParsedSkill(name="Python")],
        )

        overrides = ProfileInput(
            full_name="Human Name",
            email="parsed@example.com",
            headline="Human Headline",
        )

        profile_id = await service.accept_parsed_resume(parsed, overrides)
        loaded = await repo.get_with_children(profile_id)
        assert loaded is not None
        assert loaded.full_name == "Human Name"
        assert loaded.headline == "Human Headline"

    async def test_accept_without_overrides(self, async_session: AsyncSession) -> None:
        repo = SQLAlchemyUserProfileRepository(async_session)
        service = ProfileIntakeService(user_profile_repo=repo, session=async_session)

        parsed = ParsedResume(
            source_filename="cv.docx",
            full_name="Direct Accept",
            email="direct@example.com",
            skills=[ParsedSkill(name="Rust")],
        )

        profile_id = await service.accept_parsed_resume(parsed, None)
        loaded = await repo.get_with_children(profile_id)
        assert loaded is not None
        assert loaded.full_name == "Direct Accept"
        assert len(loaded.skills) == 1
