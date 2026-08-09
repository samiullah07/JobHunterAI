"""SQLAlchemy ORM models — all tables for the JobHunter schema."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.domain.enums import (
    ApplicationStatus,
    EmploymentType,
    FeedbackType,
    JobSource,
    NotificationChannel,
    RemotePolicy,
)
from jobhunter.infrastructure.db.base import Base, TimestampMixin, UUIDMixin


class Company(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (Index("ix_companies_name", "name", unique=True),)

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    website: Mapped[str | None] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)

    jobs: Mapped[list[Job]] = relationship(back_populates="company")


class UserProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(300))
    headline: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    github_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    visa_status: Mapped[str | None] = mapped_column(String(200))
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(10))
    availability: Mapped[str | None] = mapped_column(String(200))
    writing_style: Mapped[str | None] = mapped_column(Text)
    preferred_locations: Mapped[list[Any] | None] = mapped_column(JSONB)
    remote_preference: Mapped[str | None] = mapped_column(
        Enum(RemotePolicy, native_enum=True, name="remotepolicy")
    )
    employment_types: Mapped[list[Any] | None] = mapped_column(JSONB)
    languages: Mapped[list[Any] | None] = mapped_column(JSONB)
    keywords: Mapped[list[Any] | None] = mapped_column(JSONB)
    preferred_industries: Mapped[list[Any] | None] = mapped_column(JSONB)
    embedding: Mapped[Any | None] = mapped_column(Vector(384))

    work_experiences: Mapped[list[WorkExperience]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    educations: Mapped[list[Education]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    certifications: Mapped[list[Certification]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skills: Mapped[list[Skill]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(back_populates="profile")
    resume_versions: Mapped[list[ResumeVersion]] = relationship(back_populates="profile")
    cover_letter_versions: Mapped[list[CoverLetterVersion]] = relationship(back_populates="profile")
    match_scores: Mapped[list[MatchScore]] = relationship(back_populates="profile")


class WorkExperience(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "work_experiences"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[list[Any] | None] = mapped_column(JSONB)
    technologies: Mapped[list[Any] | None] = mapped_column(JSONB)

    profile: Mapped[UserProfile] = relationship(back_populates="work_experiences")


class Education(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "educations"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    institution: Mapped[str] = mapped_column(String(500), nullable=False)
    degree: Mapped[str] = mapped_column(String(300), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(300))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    gpa: Mapped[float | None] = mapped_column(Float)

    profile: Mapped[UserProfile] = relationship(back_populates="educations")


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1000))
    technologies: Mapped[list[Any] | None] = mapped_column(JSONB)
    highlights: Mapped[list[Any] | None] = mapped_column(JSONB)

    profile: Mapped[UserProfile] = relationship(back_populates="projects")


class Certification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "certifications"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    credential_url: Mapped[str | None] = mapped_column(String(1000))

    profile: Mapped[UserProfile] = relationship(back_populates="certifications")


class Skill(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (Index("ix_skills_profile_name", "profile_id", "name"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(200))
    proficiency: Mapped[str | None] = mapped_column(String(100))

    profile: Mapped[UserProfile] = relationship(back_populates="skills")


class Job(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
        Index("ix_jobs_company_name", "company_name"),
    )

    source: Mapped[str] = mapped_column(
        Enum(JobSource, native_enum=True, name="jobsource"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL")
    )
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str | None] = mapped_column(String(500))
    remote_policy: Mapped[str | None] = mapped_column(
        Enum(RemotePolicy, native_enum=True, name="remotepolicy", create_constraint=False)
    )
    employment_type: Mapped[str | None] = mapped_column(
        Enum(EmploymentType, native_enum=True, name="employmenttype")
    )
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(10))
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_parsed: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    embedding: Mapped[Any | None] = mapped_column(Vector(384))

    company: Mapped[Company | None] = relationship(back_populates="jobs")
    applications: Mapped[list[Application]] = relationship(back_populates="job")
    match_scores: Mapped[list[MatchScore]] = relationship(back_populates="job")
    resume_versions: Mapped[list[ResumeVersion]] = relationship(back_populates="job")
    cover_letter_versions: Mapped[list[CoverLetterVersion]] = relationship(back_populates="job")
    ats_reports: Mapped[list[AtsReport]] = relationship(back_populates="job")


class MatchScore(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "match_scores"
    __table_args__ = (Index("ix_match_scores_job_profile", "job_id", "profile_id"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    overall: Mapped[float] = mapped_column(Float, nullable=False)
    components: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rationale: Mapped[str | None] = mapped_column(Text)
    passed_prefilter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    prefilter_reasons: Mapped[list[Any] | None] = mapped_column(JSONB)
    similarity: Mapped[float | None] = mapped_column(Float)

    job: Mapped[Job] = relationship(back_populates="match_scores")
    profile: Mapped[UserProfile] = relationship(back_populates="match_scores")


class ResumeVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "resume_versions"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    version_label: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    storage_keys: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    profile: Mapped[UserProfile] = relationship(back_populates="resume_versions")
    job: Mapped[Job | None] = relationship(back_populates="resume_versions")
    ats_reports: Mapped[list[AtsReport]] = relationship(back_populates="resume_version")


class CoverLetterVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cover_letter_versions"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    version_label: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    storage_keys: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    profile: Mapped[UserProfile] = relationship(back_populates="cover_letter_versions")
    job: Mapped[Job | None] = relationship(back_populates="cover_letter_versions")


class AtsReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ats_reports"

    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_keywords: Mapped[list[Any] | None] = mapped_column(JSONB)
    missing_keywords: Mapped[list[Any] | None] = mapped_column(JSONB)
    suggestions: Mapped[list[Any] | None] = mapped_column(JSONB)

    resume_version: Mapped[ResumeVersion] = relationship(back_populates="ats_reports")
    job: Mapped[Job] = relationship(back_populates="ats_reports")


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "profile_id", name="uq_applications_job_profile"),
        Index("ix_applications_status", "status"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL")
    )
    cover_letter_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cover_letter_versions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        Enum(ApplicationStatus, native_enum=True, name="applicationstatus"),
        default=ApplicationStatus.SAVED,
        nullable=False,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    offer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="applications")
    profile: Mapped[UserProfile] = relationship(back_populates="applications")
    answers: Mapped[list[ApplicationAnswer]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    screenshots: Mapped[list[Screenshot]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(back_populates="application")
    feedback_events: Mapped[list[FeedbackEvent]] = relationship(back_populates="application")
    approval_tokens: Mapped[list[ApprovalToken]] = relationship(back_populates="application")


class ApplicationAnswer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "application_answers"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)

    application: Mapped[Application] = relationship(back_populates="answers")


class Screenshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "screenshots"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    step_label: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    application: Mapped[Application] = relationship(back_populates="screenshots")


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL")
    )
    channel: Mapped[str] = mapped_column(
        Enum(NotificationChannel, native_enum=True, name="notificationchannel"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    success: Mapped[bool] = mapped_column(Boolean, default=False)

    application: Mapped[Application | None] = relationship(back_populates="notifications")


class FeedbackEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "feedback_events"

    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL")
    )
    feedback_type: Mapped[str] = mapped_column(
        Enum(FeedbackType, native_enum=True, name="feedbacktype"), nullable=False
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    application: Mapped[Application | None] = relationship(back_populates="feedback_events")


class ApprovalToken(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "approval_tokens"
    __table_args__ = (
        Index("ix_approval_tokens_approval_hash", "approval_hash", unique=True),
        Index("ix_approval_tokens_application_id", "application_id"),
    )

    approval_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="SET NULL")
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    application: Mapped[Application | None] = relationship(back_populates="approval_tokens")
