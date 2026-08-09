"""Résumé generation API router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.adapters.generation.llm_resume_generator import LlmResumeGenerator
from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
from jobhunter.adapters.storage.local_storage import LocalStorageService
from jobhunter.application.use_cases.resume_generation import ResumeGenerationService
from jobhunter.config import get_settings
from jobhunter.domain.resume import ResumeGenerationResult
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.ats_report import SQLAlchemyAtsReportRepository
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.resume_version import (
    SQLAlchemyResumeVersionRepository,
)
from jobhunter.infrastructure.repositories.user_profile import (
    SQLAlchemyUserProfileRepository,
)

router = APIRouter(prefix="/profiles", tags=["resumes"])


def _get_resume_service(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ResumeGenerationService:
    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
    generator = LlmResumeGenerator(llm_client=llm)
    storage = LocalStorageService(settings.storage_local_dir)

    return ResumeGenerationService(
        generator=generator,
        job_repo=SQLAlchemyJobRepository(session),
        profile_repo=SQLAlchemyUserProfileRepository(session),
        resume_version_repo=SQLAlchemyResumeVersionRepository(session),
        ats_report_repo=SQLAlchemyAtsReportRepository(session),
        storage=storage,
        session=session,
    )


@router.post("/{profile_id}/resumes")
async def generate_resume(
    profile_id: uuid.UUID,
    job_id: uuid.UUID,
    service: ResumeGenerationService = Depends(_get_resume_service),  # noqa: B008
) -> ResumeGenerationResult:
    try:
        result = await service.generate_for_job(profile_id, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if result.fabrication_detected:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Fabrication detected — résumé not persisted",
                "violations": result.fabrication_report.violations,
            },
        )
    return result


@router.get("/resumes/{resume_version_id}")
async def get_resume_version(
    resume_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyResumeVersionRepository(session)
    version = await repo.get(resume_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Resume version not found")
    return {
        "id": str(version.id),
        "profile_id": str(version.profile_id),
        "job_id": str(version.job_id) if version.job_id else None,
        "version_label": version.version_label,
        "storage_keys": version.storage_keys,
    }
