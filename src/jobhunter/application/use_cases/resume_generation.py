"""Résumé generation use case — orchestrates tailoring, validation, rendering, storage."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import structlog

from jobhunter.adapters.generation.llm_resume_generator import MalformedResumeError
from jobhunter.application.services import ats_analyzer, fabrication_validator
from jobhunter.application.services.ats_analyzer import extract_keywords
from jobhunter.domain.resume import ResumeGenerationResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.adapters.storage.local_storage import LocalStorageService
    from jobhunter.application.ports.resume_generator import ResumeGenerator
    from jobhunter.application.repositories.ats_report import AtsReportRepository
    from jobhunter.application.repositories.job import JobRepository
    from jobhunter.application.repositories.resume_version import ResumeVersionRepository
    from jobhunter.application.repositories.user_profile import UserProfileRepository

logger = structlog.get_logger()


class ResumeGenerationService:
    """Orchestrates résumé generation with anti-fabrication validation."""

    def __init__(
        self,
        generator: ResumeGenerator,
        job_repo: JobRepository,
        profile_repo: UserProfileRepository,
        resume_version_repo: ResumeVersionRepository,
        ats_report_repo: AtsReportRepository,
        storage: LocalStorageService,
        session: AsyncSession,
    ) -> None:
        self._generator = generator
        self._job_repo = job_repo
        self._profile_repo = profile_repo
        self._resume_version_repo = resume_version_repo
        self._ats_report_repo = ats_report_repo
        self._storage = storage
        self._session = session

    async def generate_for_job(
        self,
        profile_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        reject_on_fabrication: bool = True,
    ) -> ResumeGenerationResult:
        from jobhunter.adapters.rendering import resume_renderer
        from jobhunter.infrastructure.db.models import AtsReport, ResumeVersion

        profile = await self._profile_repo.get_with_children(profile_id)
        if profile is None:
            msg = f"Profile {profile_id} not found"
            raise ValueError(msg)

        job = await self._job_repo.get(job_id)
        if job is None:
            msg = f"Job {job_id} not found"
            raise ValueError(msg)

        try:
            tailored = await self._generator.generate(profile, job)
        except MalformedResumeError as exc:
            logger.warning("resume_generation_malformed", error=str(exc))
            from jobhunter.domain.resume import FabricationReport

            return ResumeGenerationResult(
                fabrication_detected=True,
                fabrication_report=FabricationReport(
                    is_clean=False,
                    violations=[f"LLM output malformed: {exc}"],
                ),
            )

        fab_report = fabrication_validator.validate(tailored, profile)

        if not fab_report.is_clean:
            logger.warning(
                "fabrication_detected",
                profile_id=str(profile_id),
                job_id=str(job_id),
                violations=fab_report.violations,
            )
            if reject_on_fabrication:
                return ResumeGenerationResult(
                    fabrication_detected=True,
                    fabrication_report=fab_report,
                )

        # Render all formats
        json_str = resume_renderer.to_json(tailored)
        md_str = resume_renderer.to_markdown(tailored)
        docx_bytes = resume_renderer.to_docx(tailored)
        html_str = resume_renderer.to_html(tailored)
        pdf_bytes = await resume_renderer.to_pdf(html_str)

        # Store files
        version_id = uuid.uuid4()
        base_key = f"resumes/{version_id}"
        storage_keys: dict[str, str] = {}

        async with self._session.begin_nested():
            storage_keys["json"] = await self._storage.store(
                f"{base_key}/resume.json", json_str.encode()
            )
            storage_keys["markdown"] = await self._storage.store(
                f"{base_key}/resume.md", md_str.encode()
            )
            storage_keys["docx"] = await self._storage.store(f"{base_key}/resume.docx", docx_bytes)
            storage_keys["pdf"] = await self._storage.store(f"{base_key}/resume.pdf", pdf_bytes)

        # ATS analysis
        job_keywords = extract_keywords(job.description_raw)
        ats_result = ats_analyzer.analyze(md_str, job_keywords)

        # Persist ResumeVersion + AtsReport
        resume_version = ResumeVersion(
            id=version_id,
            profile_id=profile_id,
            job_id=job_id,
            version_label=f"tailored-{job.title[:50]}",
            canonical_json=tailored.model_dump(mode="json"),
            storage_keys=storage_keys,
        )

        async with self._session.begin_nested():
            self._session.add(resume_version)
            await self._session.flush()

        ats_report = AtsReport(
            id=uuid.uuid4(),
            resume_version_id=version_id,
            job_id=job_id,
            score=ats_result.score,
            matched_keywords=ats_result.matched_keywords,
            missing_keywords=ats_result.missing_keywords,
            suggestions=ats_result.suggestions,
        )

        async with self._session.begin_nested():
            self._session.add(ats_report)
            await self._session.flush()

        await self._session.commit()

        return ResumeGenerationResult(
            resume_version_id=str(version_id),
            storage_keys=storage_keys,
            ats_analysis=ats_result,
            fabrication_report=fab_report,
            fabrication_detected=not fab_report.is_clean,
        )
