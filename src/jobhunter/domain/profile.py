"""Pure domain DTOs for user profile and parsed résumé data.

These are the source-of-truth schemas for profile intake. The ParsedResume model
represents a PROPOSAL from the parser — nothing in it is considered "verified" until
the human calls accept_parsed_resume.

Design choice (Option A): ParsedResume uses its own LENIENT child types that accept
LLM-JSON coercion (e.g. ISO date strings → date). ProfileInput and its children stay
STRICT — they are the verified path and reject silent type coercion. This separation
enforces the integrity rule: only data that passes through accept_parsed_resume (and
thus re-validates via strict ProfileInput) becomes trusted.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from jobhunter.domain.enums import EmploymentType, RemotePolicy

# =============================================================================
# VERIFIED PATH — strict validation, no silent type coercion
# =============================================================================


class ProfileContact(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    phone: str | None = None
    location: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    website_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("github_url", "linkedin_url", "website_url", "portfolio_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.match(r"https?://", v):
            msg = "URL must start with http:// or https://"
            raise ValueError(msg)
        return v


class WorkExperienceInput(BaseModel):
    model_config = ConfigDict(strict=True)

    company_name: str
    title: str
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] | None = None
    technologies: list[str] | None = None


class EducationInput(BaseModel):
    model_config = ConfigDict(strict=True)

    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: date
    end_date: date | None = None
    gpa: float | None = None


class ProjectInput(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    description: str | None = None
    url: str | None = None
    technologies: list[str] | None = None
    highlights: list[str] | None = None

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.match(r"https?://", v):
            msg = "URL must start with http:// or https://"
            raise ValueError(msg)
        return v


class CertificationInput(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    issuer: str
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_url: str | None = None

    @field_validator("credential_url", mode="before")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.match(r"https?://", v):
            msg = "URL must start with http:// or https://"
            raise ValueError(msg)
        return v


class SkillInput(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    category: str | None = None
    proficiency: str | None = None


class ProfileInput(BaseModel):
    """Full profile submission — all scalar fields plus child collections.

    STRICT: rejects silent type coercion. This is the verified data path —
    only correctly-typed data can be persisted as a trusted profile.
    """

    model_config = ConfigDict(strict=True)

    full_name: str
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    website_url: str | None = None
    portfolio_url: str | None = None
    visa_status: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    availability: str | None = None
    writing_style: str | None = None
    remote_preference: RemotePolicy | None = None
    employment_types: list[EmploymentType] | None = None
    languages: list[str] | None = None
    keywords: list[str] | None = None
    preferred_locations: list[str] | None = None
    preferred_industries: list[str] | None = None

    work_experiences: list[WorkExperienceInput] | None = None
    educations: list[EducationInput] | None = None
    projects: list[ProjectInput] | None = None
    certifications: list[CertificationInput] | None = None
    skills: list[SkillInput] | None = None

    @field_validator("github_url", "linkedin_url", "website_url", "portfolio_url", mode="before")
    @classmethod
    def validate_urls(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.match(r"https?://", v):
            msg = "URL must start with http:// or https://"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def salary_range_valid(self) -> ProfileInput:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            msg = "salary_min must be <= salary_max"
            raise ValueError(msg)
        return self


# =============================================================================
# PARSED PATH — lenient validation, accepts LLM-JSON coercion (strings → dates,
# numeric strings → floats, etc). These are PROPOSALS, not verified data.
# =============================================================================


class ParsedWorkExperience(BaseModel):
    model_config = ConfigDict(strict=False)

    company_name: str
    title: str
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] | None = None
    technologies: list[str] | None = None


class ParsedEducation(BaseModel):
    model_config = ConfigDict(strict=False)

    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: date
    end_date: date | None = None
    gpa: float | None = None


class ParsedProject(BaseModel):
    model_config = ConfigDict(strict=False)

    name: str
    description: str | None = None
    url: str | None = None
    technologies: list[str] | None = None
    highlights: list[str] | None = None


class ParsedCertification(BaseModel):
    model_config = ConfigDict(strict=False)

    name: str
    issuer: str
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_url: str | None = None


class ParsedSkill(BaseModel):
    model_config = ConfigDict(strict=False)

    name: str
    category: str | None = None
    proficiency: str | None = None


class ParsedResume(BaseModel):
    """Raw structured output from the résumé parser — a PROPOSAL, not verified data.

    Every field is Optional because the parser does best-effort extraction.
    The confidence map indicates the parser's certainty per field (0.0–1.0).
    Nothing here is trusted until the human calls accept_parsed_resume.

    Uses LENIENT child types (ParsedWorkExperience, etc.) that accept LLM-JSON
    coercion (ISO date strings → date, numeric strings → float). The strict
    WorkExperienceInput types are only used on the verified ProfileInput path.
    """

    model_config = ConfigDict(strict=False)

    source_filename: str
    confidence: dict = {}

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    website_url: str | None = None
    portfolio_url: str | None = None
    visa_status: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    availability: str | None = None
    writing_style: str | None = None
    remote_preference: RemotePolicy | None = None
    employment_types: list[EmploymentType] | None = None
    languages: list[str] | None = None
    keywords: list[str] | None = None
    preferred_locations: list[str] | None = None
    preferred_industries: list[str] | None = None

    work_experiences: list[ParsedWorkExperience] | None = None
    educations: list[ParsedEducation] | None = None
    projects: list[ParsedProject] | None = None
    certifications: list[ParsedCertification] | None = None
    skills: list[ParsedSkill] | None = None
