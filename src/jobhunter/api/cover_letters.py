"""Cover letter generation API router."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.adapters.generation.llm_cover_letter_generator import (
    LlmCoverLetterGenerator,
)
from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
from jobhunter.adapters.storage.local_storage import LocalStorageService
from jobhunter.application.use_cases.cover_letter_generation import (
    CoverLetterGenerationService,
)
from jobhunter.config import get_settings
from jobhunter.domain.cover_letter import CoverLetterGenerationResult
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.cover_letter_version import (
    SQLAlchemyCoverLetterVersionRepository,
)
from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
from jobhunter.infrastructure.repositories.match_score import (
    SQLAlchemyMatchScoreRepository,
)
from jobhunter.infrastructure.repositories.user_profile import (
    SQLAlchemyUserProfileRepository,
)

router = APIRouter(prefix="/profiles", tags=["cover-letters"])


def _get_cover_letter_service(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> CoverLetterGenerationService:
    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
    generator = LlmCoverLetterGenerator(llm_client=llm)
    storage = LocalStorageService(settings.storage_local_dir)

    return CoverLetterGenerationService(
        generator=generator,
        job_repo=SQLAlchemyJobRepository(session),
        profile_repo=SQLAlchemyUserProfileRepository(session),
        match_score_repo=SQLAlchemyMatchScoreRepository(session),
        cover_letter_version_repo=SQLAlchemyCoverLetterVersionRepository(session),
        storage=storage,
        session=session,
    )


@router.post("/{profile_id}/cover-letters")
async def generate_cover_letter(
    profile_id: uuid.UUID,
    job_id: uuid.UUID,
    service: CoverLetterGenerationService = Depends(_get_cover_letter_service),  # noqa: B008
) -> CoverLetterGenerationResult:
    try:
        result = await service.generate_for_job(profile_id, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if result.below_threshold or result.no_score:
        raise HTTPException(status_code=409, detail=result.reason)

    if result.fabrication_detected:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Fabrication detected — cover letter not persisted",
                "violations": result.fabrication_report.violations,
            },
        )
    return result


@router.get("/cover-letters/{cover_letter_version_id}")
async def get_cover_letter_version(
    cover_letter_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyCoverLetterVersionRepository(session)
    version = await repo.get(cover_letter_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Cover letter version not found")
    return {
        "id": str(version.id),
        "profile_id": str(version.profile_id),
        "job_id": str(version.job_id) if version.job_id else None,
        "version_label": version.version_label,
        "storage_keys": version.storage_keys,
    }
