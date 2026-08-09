"""Unit tests for cover letter fabrication validator — both directions."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from jobhunter.application.services.fabrication_validator import validate_cover_letter
from jobhunter.domain.cover_letter import CoverLetter


def _make_profile() -> MagicMock:
    profile = MagicMock()
    profile.full_name = "Jane Doe"
    profile.email = "jane@example.com"

    skill1 = MagicMock()
    skill1.name = "Python"
    skill2 = MagicMock()
    skill2.name = "FastAPI"
    skill3 = MagicMock()
    skill3.name = "PostgreSQL"
    profile.skills = [skill1, skill2, skill3]

    exp = MagicMock()
    exp.company_name = "Acme Corp"
    exp.title = "Senior Engineer"
    exp.start_date = date(2020, 1, 1)
    exp.end_date = None
    exp.is_current = True
    exp.technologies = ["Python", "FastAPI", "Docker"]
    profile.work_experiences = [exp]

    edu = MagicMock()
    edu.institution = "MIT"
    edu.degree = "B.S. Computer Science"
    edu.field_of_study = "Computer Science"
    edu.start_date = date(2014, 9, 1)
    edu.end_date = date(2018, 5, 1)
    profile.educations = [edu]

    profile.projects = []

    cert = MagicMock()
    cert.name = "AWS Solutions Architect"
    profile.certifications = [cert]

    return profile


def _make_clean_letter() -> CoverLetter:
    """A letter using ONLY verified profile facts + legitimate target company reference."""
    return CoverLetter(
        salutation="Dear Hiring Manager,",
        opening=(
            "I am writing to express my interest in the Backend Developer position at TechCo."
        ),
        body_paragraphs=[
            "In my current role as Senior Engineer at Acme Corp, I have built "
            "scalable services using Python and FastAPI. This experience aligns "
            "directly with the requirements of the Backend Developer role.",
            "I am excited to bring my backend experience to TechCo and "
            "contribute to your engineering team's mission.",
        ],
        closing=(
            "Thank you for considering my application. I look forward to "
            "discussing how my Python expertise can benefit TechCo."
        ),
        signature="Sincerely, Jane Doe",
        company_name="TechCo",
        role="Backend Developer",
    )


class TestCleanCoverLetter:
    def test_clean_letter_with_profile_tech_is_valid(self) -> None:
        """Letter referencing only verified tech (Python, FastAPI) → clean."""
        profile = _make_profile()
        letter = _make_clean_letter()
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is True
        assert report.violations == []

    def test_target_company_in_prose_not_flagged(self) -> None:
        """The target company name appearing in opening/body → NOT flagged."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear TechCo Hiring Team,",
            opening="I am thrilled about the opportunity at TechCo.",
            body_paragraphs=[
                "TechCo's mission resonates deeply with my background in Python.",
            ],
            closing="I would love to join TechCo's engineering team.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is True
        assert report.violations == []

    def test_aspirational_framing_no_false_positive(self) -> None:
        """Motivational prose with NO factual claims → clean (no false positive)."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am drawn to your mission of transforming the industry.",
            body_paragraphs=[
                "I am eager to contribute my skills and grow as an engineer.",
                "The opportunity to collaborate with talented peers excites me.",
            ],
            closing="I look forward to discussing this opportunity further.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is True
        assert report.violations == []


class TestInventedTechInCoverLetter:
    def test_invented_technology_flagged(self) -> None:
        """Claiming 'Kubernetes experience' when not in profile → violation."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am writing about the Backend Developer role at TechCo.",
            body_paragraphs=[
                "My extensive Kubernetes and Terraform experience makes me "
                "an ideal candidate for this infrastructure-focused role.",
            ],
            closing="Thank you for your consideration.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is False
        assert any("Kubernetes" in v for v in report.violations)
        assert any("Terraform" in v for v in report.violations)

    def test_regression_invented_tech_would_fail_if_pass(self) -> None:
        """Directly asserts the violation is present — fails if check is disabled."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am interested in the role at TechCo.",
            body_paragraphs=["I have deep expertise in Istio service mesh."],
            closing="Thank you.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is False
        assert len(report.violations) >= 1
        assert any("Istio" in v for v in report.violations)


class TestInventedEmployerInCoverLetter:
    def test_claim_of_working_at_unknown_employer_flagged(self) -> None:
        """Claiming 'worked at FakeStartup' when not in profile → violation."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am applying for the Backend Developer role at TechCo.",
            body_paragraphs=[
                "During my time at Acme Corp, I built Python services.",
                "I also worked at FakeStartup where I led the platform team.",
            ],
            closing="Thank you.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is False
        assert any("FakeStartup" in v for v in report.violations)

    def test_target_company_in_work_phrase_not_flagged(self) -> None:
        """'eager to work at TechCo' should NOT trigger employer fabrication."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am writing about the Backend Developer position.",
            body_paragraphs=[
                "I am eager to work at TechCo and contribute to the team.",
            ],
            closing="Thank you.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is True


class TestInventedCredentialInCoverLetter:
    def test_invented_certification_flagged(self) -> None:
        """Claiming a cert not in profile → violation."""
        profile = _make_profile()
        letter = CoverLetter(
            salutation="Dear Hiring Manager,",
            opening="I am applying for the role at TechCo.",
            body_paragraphs=[
                "My certification in Google Cloud Professional validates "
                "my cloud architecture skills.",
            ],
            closing="Thank you.",
            signature="Sincerely, Jane Doe",
            company_name="TechCo",
            role="Backend Developer",
        )
        report = validate_cover_letter(letter, profile)
        assert report.is_clean is False
        assert any("Google Cloud" in v for v in report.violations)
