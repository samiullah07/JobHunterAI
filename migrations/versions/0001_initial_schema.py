"""Initial schema — all tables, enums, indexes, constraints.

Revision ID: 0001
Revises:
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

applicationstatus = postgresql.ENUM(
    "saved",
    "ready_for_review",
    "approved",
    "submitted",
    "interviewing",
    "rejected",
    "offer",
    "withdrawn",
    "skipped",
    name="applicationstatus",
    create_type=False,
)

jobsource = postgresql.ENUM(
    "linkedin",
    "indeed",
    "glassdoor",
    "wellfound",
    "greenhouse",
    "lever",
    "ashby",
    "workday",
    "remoteok",
    "ycombinator",
    "company_site",
    "other",
    name="jobsource",
    create_type=False,
)

employmenttype = postgresql.ENUM(
    "full_time",
    "part_time",
    "contract",
    "internship",
    "temporary",
    name="employmenttype",
    create_type=False,
)

remotepolicy = postgresql.ENUM(
    "remote",
    "hybrid",
    "onsite",
    "unspecified",
    name="remotepolicy",
    create_type=False,
)

notificationchannel = postgresql.ENUM(
    "email",
    "slack",
    "discord",
    "telegram",
    "push",
    name="notificationchannel",
    create_type=False,
)

feedbacktype = postgresql.ENUM(
    "human_edit",
    "approved",
    "rejected",
    "skipped",
    "regenerated",
    name="feedbacktype",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    applicationstatus.create(op.get_bind(), checkfirst=True)
    jobsource.create(op.get_bind(), checkfirst=True)
    employmenttype.create(op.get_bind(), checkfirst=True)
    remotepolicy.create(op.get_bind(), checkfirst=True)
    notificationchannel.create(op.get_bind(), checkfirst=True)
    feedbacktype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("website", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_preferred", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_blacklisted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_companies_name", "companies", ["name"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(300), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column("headline", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("visa_status", sa.String(200), nullable=True),
        sa.Column("salary_min", sa.Float, nullable=True),
        sa.Column("salary_max", sa.Float, nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True),
        sa.Column("availability", sa.String(200), nullable=True),
        sa.Column("writing_style", sa.Text, nullable=True),
        sa.Column("preferred_locations", postgresql.JSONB, nullable=True),
        sa.Column("remote_preference", remotepolicy, nullable=True),
        sa.Column("employment_types", postgresql.JSONB, nullable=True),
        sa.Column("languages", postgresql.JSONB, nullable=True),
        sa.Column("keywords", postgresql.JSONB, nullable=True),
        sa.Column("preferred_industries", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "work_experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("achievements", postgresql.JSONB, nullable=True),
        sa.Column("technologies", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "educations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("institution", sa.String(500), nullable=False),
        sa.Column("degree", sa.String(300), nullable=False),
        sa.Column("field_of_study", sa.String(300), nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("gpa", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("technologies", postgresql.JSONB, nullable=True),
        sa.Column("highlights", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("issuer", sa.String(500), nullable=False),
        sa.Column("issue_date", sa.Date, nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True),
        sa.Column("credential_url", sa.String(1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("proficiency", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_skills_profile_name", "skills", ["profile_id", "name"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", jobsource, nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("remote_policy", remotepolicy, nullable=True),
        sa.Column("employment_type", employmenttype, nullable=True),
        sa.Column("salary_min", sa.Float, nullable=True),
        sa.Column("salary_max", sa.Float, nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True),
        sa.Column("description_raw", sa.Text, nullable=False),
        sa.Column("description_parsed", postgresql.JSONB, nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
    )
    op.create_index("ix_jobs_company_name", "jobs", ["company_name"])

    op.create_table(
        "match_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overall", sa.Float, nullable=False),
        sa.Column("components", postgresql.JSONB, nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_match_scores_job_profile", "match_scores", ["job_id", "profile_id"])

    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version_label", sa.String(200), nullable=False),
        sa.Column("canonical_json", postgresql.JSONB, nullable=True),
        sa.Column("storage_keys", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "cover_letter_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version_label", sa.String(200), nullable=False),
        sa.Column("body_markdown", sa.Text, nullable=False),
        sa.Column("storage_keys", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "ats_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("matched_keywords", postgresql.JSONB, nullable=True),
        sa.Column("missing_keywords", postgresql.JSONB, nullable=True),
        sa.Column("suggestions", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resume_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cover_letter_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cover_letter_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", applicationstatus, nullable=False, server_default=sa.text("'saved'")),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offer_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("job_id", "profile_id", name="uq_applications_job_profile"),
    )
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "application_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "screenshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_label", sa.String(300), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel", notificationchannel, nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "feedback_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("feedback_type", feedbacktype, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("feedback_events")
    op.drop_table("notifications")
    op.drop_table("screenshots")
    op.drop_table("application_answers")
    op.drop_table("applications")
    op.drop_table("ats_reports")
    op.drop_table("cover_letter_versions")
    op.drop_table("resume_versions")
    op.drop_table("match_scores")
    op.drop_table("jobs")
    op.drop_table("skills")
    op.drop_table("certifications")
    op.drop_table("projects")
    op.drop_table("educations")
    op.drop_table("work_experiences")
    op.drop_table("user_profiles")
    op.drop_table("companies")

    feedbacktype.drop(op.get_bind(), checkfirst=True)
    notificationchannel.drop(op.get_bind(), checkfirst=True)
    remotepolicy.drop(op.get_bind(), checkfirst=True)
    employmenttype.drop(op.get_bind(), checkfirst=True)
    jobsource.drop(op.get_bind(), checkfirst=True)
    applicationstatus.drop(op.get_bind(), checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS vector")
