"""Unit tests for domain enums."""

from jobhunter.domain.enums import (
    ApplicationStatus,
    ArtifactFormat,
    EmploymentType,
    FeedbackType,
    JobSource,
    NotificationChannel,
    RemotePolicy,
)


def test_application_status_values() -> None:
    assert len(ApplicationStatus) == 9
    assert ApplicationStatus.SAVED.value == "saved"
    assert ApplicationStatus.READY_FOR_REVIEW.value == "ready_for_review"
    assert ApplicationStatus.APPROVED.value == "approved"
    assert ApplicationStatus.SUBMITTED.value == "submitted"
    assert ApplicationStatus.INTERVIEWING.value == "interviewing"
    assert ApplicationStatus.REJECTED.value == "rejected"
    assert ApplicationStatus.OFFER.value == "offer"
    assert ApplicationStatus.WITHDRAWN.value == "withdrawn"
    assert ApplicationStatus.SKIPPED.value == "skipped"


def test_job_source_values() -> None:
    assert len(JobSource) == 12
    assert JobSource.LINKEDIN.value == "linkedin"
    assert JobSource.YCOMBINATOR.value == "ycombinator"
    assert JobSource.COMPANY_SITE.value == "company_site"


def test_artifact_format_values() -> None:
    assert len(ArtifactFormat) == 4
    assert ArtifactFormat.JSON.value == "json"
    assert ArtifactFormat.PDF.value == "pdf"


def test_employment_type_values() -> None:
    assert len(EmploymentType) == 5
    assert EmploymentType.FULL_TIME.value == "full_time"


def test_remote_policy_values() -> None:
    assert len(RemotePolicy) == 4
    assert RemotePolicy.REMOTE.value == "remote"
    assert RemotePolicy.UNSPECIFIED.value == "unspecified"


def test_notification_channel_values() -> None:
    assert len(NotificationChannel) == 5
    assert NotificationChannel.EMAIL.value == "email"


def test_feedback_type_values() -> None:
    assert len(FeedbackType) == 5
    assert FeedbackType.HUMAN_EDIT.value == "human_edit"
    assert FeedbackType.REGENERATED.value == "regenerated"


def test_strenum_is_string() -> None:
    assert isinstance(ApplicationStatus.SAVED, str)
    assert f"status={ApplicationStatus.SAVED}" == "status=saved"
