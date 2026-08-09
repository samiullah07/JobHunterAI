"""Unit tests for domain profile schemas — validators and constraints."""

from datetime import date

import pytest
from pydantic import ValidationError

from jobhunter.domain.enums import EmploymentType, RemotePolicy
from jobhunter.domain.profile import (
    CertificationInput,
    ParsedResume,
    ParsedSkill,
    ParsedWorkExperience,
    ProfileContact,
    ProfileInput,
    ProjectInput,
    SkillInput,
    WorkExperienceInput,
)


class TestProfileContact:
    def test_valid_contact(self) -> None:
        c = ProfileContact(
            email="user@example.com",
            github_url="https://github.com/user",
        )
        assert c.email == "user@example.com"
        assert c.github_url == "https://github.com/user"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError, match="email"):
            ProfileContact(email="not-an-email")

    def test_invalid_url(self) -> None:
        with pytest.raises(ValidationError, match="http"):
            ProfileContact(email="user@example.com", github_url="ftp://bad")

    def test_none_urls_are_fine(self) -> None:
        c = ProfileContact(email="a@b.com")
        assert c.github_url is None


class TestProfileInput:
    def test_salary_range_valid(self) -> None:
        p = ProfileInput(
            full_name="Jane Doe",
            email="jane@example.com",
            salary_min=80000.0,
            salary_max=120000.0,
        )
        assert p.salary_min == 80000.0

    def test_salary_range_invalid(self) -> None:
        with pytest.raises(ValidationError, match="salary_min"):
            ProfileInput(
                full_name="Jane Doe",
                email="jane@example.com",
                salary_min=150000.0,
                salary_max=100000.0,
            )

    def test_invalid_email_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProfileInput(full_name="Jane", email="bad")

    def test_url_validation(self) -> None:
        with pytest.raises(ValidationError, match="http"):
            ProfileInput(
                full_name="Jane",
                email="j@e.com",
                github_url="not-a-url",
            )

    def test_full_profile_with_children(self) -> None:
        p = ProfileInput(
            full_name="Jane Doe",
            email="jane@example.com",
            remote_preference=RemotePolicy.REMOTE,
            employment_types=[EmploymentType.FULL_TIME, EmploymentType.CONTRACT],
            work_experiences=[
                WorkExperienceInput(
                    company_name="Acme",
                    title="Engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                )
            ],
            skills=[SkillInput(name="Python")],
        )
        assert len(p.work_experiences) == 1  # type: ignore[arg-type]
        assert p.remote_preference == RemotePolicy.REMOTE

    def test_valid_profile_regression_guard(self) -> None:
        """Regression: correctly-typed input always builds fine under strict mode."""
        p = ProfileInput(
            full_name="Alice",
            email="alice@example.com",
            salary_min=90000.0,
            salary_max=140000.0,
            salary_currency="USD",
            remote_preference=RemotePolicy.HYBRID,
            employment_types=[EmploymentType.FULL_TIME],
            languages=["English", "Spanish"],
            keywords=["python", "ml"],
            work_experiences=[
                WorkExperienceInput(
                    company_name="BigCo",
                    title="Staff Engineer",
                    start_date=date(2018, 3, 1),
                    end_date=date(2023, 6, 30),
                    is_current=False,
                    achievements=["Led team of 8"],
                    technologies=["Python", "K8s"],
                )
            ],
            skills=[SkillInput(name="Python", category="Language", proficiency="Expert")],
        )
        assert p.full_name == "Alice"
        assert p.work_experiences is not None
        assert p.work_experiences[0].is_current is False


class TestStrictRejection:
    """ProfileInput MUST reject silent type coercion that strict mode catches."""

    def test_rejects_salary_as_string(self) -> None:
        """salary_min is float; a string "50000" must be rejected (no coercion)."""
        with pytest.raises(ValidationError):
            ProfileInput(
                full_name="Jane",
                email="j@e.com",
                salary_min="50000",  # type: ignore[arg-type]
            )

    def test_rejects_bool_string_in_work_experience(self) -> None:
        """is_current is bool; string "true" must be rejected under strict mode."""
        with pytest.raises(ValidationError):
            WorkExperienceInput(
                company_name="Corp",
                title="Dev",
                start_date=date(2020, 1, 1),
                is_current="true",  # type: ignore[arg-type]
            )

    def test_rejects_date_as_string_in_work_experience(self) -> None:
        """start_date is date; an ISO string must be rejected under strict mode."""
        with pytest.raises(ValidationError):
            WorkExperienceInput(
                company_name="Corp",
                title="Dev",
                start_date="2020-01-15",  # type: ignore[arg-type]
            )

    def test_rejects_list_for_string_field(self) -> None:
        """Under strict mode, a list where str is expected must be rejected."""
        with pytest.raises(ValidationError):
            ProfileInput(
                full_name="Jane",
                email="j@e.com",
                headline=["not", "a", "string"],  # type: ignore[arg-type]
            )


class TestParsedResumeLenient:
    """ParsedResume MUST accept lenient LLM-JSON coercion."""

    def test_all_optional(self) -> None:
        pr = ParsedResume(source_filename="resume.pdf")
        assert pr.full_name is None
        assert pr.confidence == {}

    def test_partial_fill(self) -> None:
        pr = ParsedResume(
            source_filename="cv.docx",
            full_name="John",
            email="john@test.com",
            confidence={"full_name": 0.95, "email": 0.8},
        )
        assert pr.full_name == "John"
        assert pr.confidence["email"] == 0.8

    def test_accepts_date_as_iso_string(self) -> None:
        """LLM returns dates as ISO strings — ParsedResume must coerce them."""
        pr = ParsedResume(
            source_filename="resume.pdf",
            work_experiences=[
                ParsedWorkExperience(
                    company_name="Acme",
                    title="Engineer",
                    start_date="2020-01-15",
                    is_current=True,
                )
            ],
        )
        assert pr.work_experiences is not None
        assert pr.work_experiences[0].start_date == date(2020, 1, 15)

    def test_accepts_bool_as_string(self) -> None:
        """LLM may return booleans as strings — lenient path coerces."""
        pr = ParsedResume(
            source_filename="resume.pdf",
            work_experiences=[
                ParsedWorkExperience(
                    company_name="X",
                    title="Y",
                    start_date="2021-06-01",
                    is_current="true",
                )
            ],
        )
        assert pr.work_experiences is not None
        assert pr.work_experiences[0].is_current is True

    def test_accepts_salary_as_string(self) -> None:
        """LLM may return numbers as strings — lenient path coerces."""
        pr = ParsedResume(
            source_filename="resume.pdf",
            salary_min="80000",
            salary_max="120000",
        )
        assert pr.salary_min == 80000.0
        assert pr.salary_max == 120000.0

    def test_accepts_missing_optional_fields(self) -> None:
        """Most fields missing — ParsedResume validates with just source_filename."""
        pr = ParsedResume(
            source_filename="minimal.pdf",
            full_name="Minimal",
            skills=[ParsedSkill(name="Go")],
        )
        assert pr.full_name == "Minimal"
        assert pr.educations is None


class TestChildModels:
    def test_work_experience(self) -> None:
        we = WorkExperienceInput(
            company_name="Corp",
            title="Dev",
            start_date=date(2019, 6, 1),
            end_date=date(2021, 12, 31),
        )
        assert we.company_name == "Corp"

    def test_project_url_validation(self) -> None:
        with pytest.raises(ValidationError, match="http"):
            ProjectInput(name="Proj", url="invalid")

    def test_project_valid_url(self) -> None:
        p = ProjectInput(name="X", url="https://example.com/x")
        assert p.url == "https://example.com/x"

    def test_certification_url_validation(self) -> None:
        with pytest.raises(ValidationError, match="http"):
            CertificationInput(name="AWS", issuer="Amazon", credential_url="bad")

    def test_certification_valid(self) -> None:
        c = CertificationInput(
            name="AWS SAA",
            issuer="Amazon",
            credential_url="https://aws.amazon.com/cert/123",
        )
        assert c.issuer == "Amazon"
