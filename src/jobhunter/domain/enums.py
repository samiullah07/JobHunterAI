"""Pure domain enumerations — no framework imports allowed."""

from enum import StrEnum


class ApplicationStatus(StrEnum):
    SAVED = "saved"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    INTERVIEWING = "interviewing"
    REJECTED = "rejected"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"
    SKIPPED = "skipped"


class JobSource(StrEnum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    WELLFOUND = "wellfound"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    REMOTEOK = "remoteok"
    YCOMBINATOR = "ycombinator"
    COMPANY_SITE = "company_site"
    OTHER = "other"


class ArtifactFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    DOCX = "docx"
    PDF = "pdf"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class RemotePolicy(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNSPECIFIED = "unspecified"


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    PUSH = "push"


class FeedbackType(StrEnum):
    HUMAN_EDIT = "human_edit"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    REGENERATED = "regenerated"
