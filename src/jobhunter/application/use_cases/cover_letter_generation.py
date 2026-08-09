"""Cover letter generation use case — orchestrates generation, validation, rendering, storage."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog

from jobhunter.adapters.generation.llm_cover_letter_generator import (
    MalformedCoverLetterError,
)
from jobhunter.application.services import fabrication_validator
from jobhunter.config import get_settings
from jobhunter.domain.cover_letter import CoverLetterGenerationResult
from jobhunter.domain.resume import FabricationReport

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.adapters.storage.local_storage import LocalStorageService
    from jobhunter.application.ports.cover_letter_generator import CoverLetterGenerator
    from jobhunter.application.repositories.cover_letter_version import (
        CoverLetterVersionRepository,
    )
    from jobhunter.application.repositories.job import JobRepository
    from jobhunter.application.repositories.match_score import MatchScoreRepository
    from jobhunter.application.repositories.user_profile import UserProfileRepository

logger = structlog.get_logger()


class CoverLetterGenerationService:
    """Orchestrates cover letter generation with threshold gating and fabrication validation."""

    def __init__(
        self,
        generator: CoverLetterGenerator,
        job_repo: JobRepository,
        profile_repo: UserProfileRepository,
        match_score_repo: MatchScoreRepository,
        cover_letter_version_repo: CoverLetterVersionRepository,
        storage: LocalStorageService,
        session: AsyncSession,
    ) -> None:
        self._generator = generator
        self._job_repo = job_repo
        self._profile_repo = profile_repo
        self._match_score_repo = match_score_repo
        self._cover_letter_version_repo = cover_letter_version_repo
        self._storage = storage
        self._session = session

    async def generate_for_job(
        self,
        profile_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        reject_on_fabrication: bool = True,
    ) -> CoverLetterGenerationResult:
        from jobhunter.adapters.rendering import cover_letter_renderer
        from jobhunter.infrastructure.db.models import CoverLetterVersion

        profile = await self._profile_repo.get_with_children(profile_id)
        if profile is None:
            msg = f"Profile {profile_id} not found"
            raise ValueError(msg)

        job = await self._job_repo.get(job_id)
        if job is None:
            msg = f"Job {job_id} not found"
            raise ValueError(msg)

        # THRESHOLD GATE: refuse if no score or below threshold
        settings = get_settings()
        match_score = await self._match_score_repo.get_for_job_profile(job_id, profile_id)

        if match_score is None:
            return CoverLetterGenerationResult(
                no_score=True,
                reason=(
                    f"No match score exists for job {job_id} and profile {profile_id}. "
                    "Score the job first."
                ),
            )

        if match_score.overall < settings.match_score_threshold:
            return CoverLetterGenerationResult(
                below_threshold=True,
                reason=(
                    f"Match score {match_score.overall:.2f} is below "
                    f"threshold {settings.match_score_threshold:.2f}. "
                    "Cover letter generation requires a passing match score."
                ),
            )

        # Generate cover letter via LLM
        try:
            letter = await self._generator.generate(profile, job)
        except MalformedCoverLetterError as exc:
            logger.warning("cover_letter_generation_malformed", error=str(exc))
            return CoverLetterGenerationResult(
                fabrication_detected=True,
                fabrication_report=FabricationReport(
                    is_clean=False,
                    violations=[f"LLM output malformed: {exc}"],
                ),
            )

        # Validate for fabrication
        fab_report = fabrication_validator.validate_cover_letter(letter, profile)

        if not fab_report.is_clean:
            logger.warning(
                "cover_letter_fabrication_detected",
                profile_id=str(profile_id),
                job_id=str(job_id),
                violations=fab_report.violations,
            )
            if reject_on_fabrication:
                return CoverLetterGenerationResult(
                    fabrication_detected=True,
                    fabrication_report=fab_report,
                )

        # Render all formats
        md_str = cover_letter_renderer.to_markdown(letter)
        docx_bytes = cover_letter_renderer.to_docx(letter)
        html_str = cover_letter_renderer.to_html(letter)
        pdf_bytes = await cover_letter_renderer.to_pdf(html_str)

        # Store files
        version_id = uuid.uuid4()
        base_key = f"coverletters/{version_id}"
        storage_keys: dict[str, str] = {}

        async with self._session.begin_nested():
            storage_keys["markdown"] = await self._storage.store(
                f"{base_key}/cover_letter.md", md_str.encode()
            )
            storage_keys["docx"] = await self._storage.store(
                f"{base_key}/cover_letter.docx", docx_bytes
            )
            storage_keys["pdf"] = await self._storage.store(
                f"{base_key}/cover_letter.pdf", pdf_bytes
            )

        # Persist CoverLetterVersion
        cover_letter_version = CoverLetterVersion(
            id=version_id,
            profile_id=profile_id,
            job_id=job_id,
            version_label=f"cover-{job.title[:50]}",
            body_markdown=md_str,
            storage_keys=storage_keys,
        )

        async with self._session.begin_nested():
            self._session.add(cover_letter_version)
            await self._session.flush()

        await self._session.commit()

        return CoverLetterGenerationResult(
            cover_letter_version_id=str(version_id),
            storage_keys=storage_keys,
            fabrication_report=fab_report,
            fabrication_detected=not fab_report.is_clean,
        )
