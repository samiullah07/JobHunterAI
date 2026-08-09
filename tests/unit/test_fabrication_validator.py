"""Unit tests for the fabrication validator — the heart of M6 integrity."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from jobhunter.application.services.fabrication_validator import validate
from jobhunter.domain.resume import (
    TailoredEducation,
    TailoredExperience,
    TailoredProject,
    TailoredResume,
    TailoredSkillGroup,
)


def _make_profile() -> MagicMock:
    """Create a verified profile with known data for validation testing."""
    profile = MagicMock()
    profile.full_name = "Jane Doe"
    profile.email = "jane@example.com"

    skill1 = MagicMock()
    skill1.name = "Python"
    skill2 = MagicMock()
    skill2.name = "PostgreSQL"
    skill3 = MagicMock()
    skill3.name = "Docker"
    profile.skills = [skill1, skill2, skill3]

    exp = MagicMock()
    exp.company_name = "Acme Corp"
    exp.title = "Senior Engineer"
    exp.start_date = date(2020, 1, 1)
    exp.end_date = None
    exp.is_current = True
    exp.technologies = ["Python", "FastAPI", "PostgreSQL"]
    profile.work_experiences = [exp]

    edu = MagicMock()
    edu.institution = "MIT"
    edu.degree = "B.S. Computer Science"
    edu.field_of_study = "Computer Science"
    edu.start_date = date(2014, 9, 1)
    edu.end_date = date(2018, 5, 1)
    profile.educations = [edu]

    proj = MagicMock()
    proj.name = "OpenWidget"
    proj.technologies = ["React", "TypeScript"]
    profile.projects = [proj]

    cert = MagicMock()
    cert.name = "AWS Solutions Architect"
    profile.certifications = [cert]

    return profile


def _make_clean_resume() -> TailoredResume:
    """A résumé using ONLY facts from the profile above."""
    return TailoredResume(
        full_name="Jane Doe",
        email="jane@example.com",
        summary="Senior Engineer with Python expertise.",
        experiences=[
            TailoredExperience(
                company="Acme Corp",
                title="Senior Engineer",
                start_date=date(2020, 1, 1),
                is_current=True,
                bullets=[
                    "Built backend services using Python and FastAPI",
                    "Managed PostgreSQL databases for high availability",
                ],
            )
        ],
        education=[
            TailoredEducation(
                institution="MIT",
                degree="B.S. Computer Science",
                field_of_study="Computer Science",
                start_date=date(2014, 9, 1),
                end_date=date(2018, 5, 1),
            )
        ],
        skills=[TailoredSkillGroup(category="Backend", skills=["Python", "PostgreSQL", "Docker"])],
        projects=[TailoredProject(name="OpenWidget", technologies=["React", "TypeScript"])],
        certifications=["AWS Solutions Architect"],
    )


class TestCleanResume:
    def test_valid_resume_is_clean(self) -> None:
        profile = _make_profile()
        resume = _make_clean_resume()
        report = validate(resume, profile)
        assert report.is_clean is True
        assert report.violations == []


class TestInventedEmployer:
    def test_invented_company_flagged(self) -> None:
        profile = _make_profile()
        resume = _make_clean_resume()
        resume.experiences.append(
            TailoredExperience(
                company="FakeCorp",
                title="VP Engineering",
                start_date=date(2018, 1, 1),
                end_date=date(2019, 12, 31),
                bullets=["Led engineering team"],
            )
        )
        report = validate(resume, profile)
        assert report.is_clean is False
        assert any("FakeCorp" in v for v in report.violations)


class TestInventedSkill:
    def test_skill_not_in_profile_flagged(self) -> None:
        profile = _make_profile()
        resume = _make_clean_resume()
        resume.skills.append(TailoredSkillGroup(category="Systems", skills=["Rust", "Zig"]))
        report = validate(resume, profile)
        assert report.is_clean is False
        assert any("Rust" in v for v in report.violations)
        assert any("Zig" in v for v in report.violations)


class TestAlteredDates:
    def test_extended_start_date_flagged(self) -> None:
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="Acme Corp",
                    title="Senior Engineer",
                    start_date=date(2019, 1, 1),  # Extended from 2020
                    is_current=True,
                    bullets=["Built services"],
                )
            ],
        )
        report = validate(resume, profile)
        assert report.is_clean is False
        assert any("start_date" in v for v in report.violations)


class TestInventedCertification:
    def test_certification_not_in_profile_flagged(self) -> None:
        profile = _make_profile()
        resume = _make_clean_resume()
        resume.certifications.append("Google Cloud Professional")
        report = validate(resume, profile)
        assert report.is_clean is False
        assert any("Google Cloud" in v for v in report.violations)


class TestInventedProject:
    def test_project_not_in_profile_flagged(self) -> None:
        profile = _make_profile()
        resume = _make_clean_resume()
        resume.projects.append(TailoredProject(name="SecretProject", technologies=["Go"]))
        report = validate(resume, profile)
        assert report.is_clean is False
        assert any("SecretProject" in v for v in report.violations)


class TestBulletTechnologyFabrication:
    """Regression guard for the bullet-level tech check.

    These tests WILL FAIL if the check is reverted to a no-op (pass).
    """

    def test_invented_tech_in_bullet_flagged(self) -> None:
        """Profile has Python/FastAPI/PostgreSQL; bullet claims Kubernetes + Terraform."""
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="Acme Corp",
                    title="Senior Engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    bullets=[
                        "Led the Kubernetes and Terraform rollout across all services",
                    ],
                )
            ],
        )
        report = validate(resume, profile)
        assert report.is_clean is False
        assert any("Kubernetes" in v for v in report.violations)
        assert any("Terraform" in v for v in report.violations)

    def test_real_profile_tech_in_bullet_no_flag(self) -> None:
        """Bullet referencing a tech that IS in the profile → no violation."""
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="Acme Corp",
                    title="Senior Engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    bullets=["Built Python services using FastAPI and PostgreSQL"],
                )
            ],
        )
        report = validate(resume, profile)
        assert report.is_clean is True
        assert report.violations == []

    def test_pure_prose_bullet_no_flag(self) -> None:
        """A bullet with ONLY generic prose / action verbs → no violation."""
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="Acme Corp",
                    title="Senior Engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    bullets=[
                        "Spearheaded cross-team delivery improving throughput by 40%",
                    ],
                )
            ],
        )
        report = validate(resume, profile)
        assert report.is_clean is True
        assert report.violations == []

    def test_violation_message_names_term_and_role(self) -> None:
        """The violation message must include the tech term and the role context."""
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="Acme Corp",
                    title="Senior Engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    bullets=["Migrated services to Istio mesh"],
                )
            ],
        )
        report = validate(resume, profile)
        assert report.is_clean is False
        assert len(report.violations) >= 1
        violation = next(v for v in report.violations if "Istio" in v)
        assert "Senior Engineer" in violation
        assert "Acme Corp" in violation
        assert "Istio" in violation


class TestLegitimateRephrasing:
    def test_case_difference_still_clean(self) -> None:
        """Company/title case differences should not false-positive."""
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="ACME CORP",
                    title="senior engineer",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    bullets=["Developed Python services"],
                )
            ],
            skills=[TailoredSkillGroup(category="Languages", skills=["python", "postgresql"])],
        )
        report = validate(resume, profile)
        assert report.is_clean is True
        assert report.violations == []

    def test_whitespace_difference_still_clean(self) -> None:
        """Extra whitespace should not false-positive."""
        profile = _make_profile()
        resume = TailoredResume(
            full_name="Jane Doe",
            email="jane@example.com",
            experiences=[
                TailoredExperience(
                    company="  Acme Corp  ",
                    title=" Senior Engineer ",
                    start_date=date(2020, 1, 1),
                    is_current=True,
                    bullets=["Built APIs"],
                )
            ],
        )
        report = validate(resume, profile)
        assert report.is_clean is True
