"""Profile API router — thin HTTP translation over the profile intake use case."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.application.ports.resume_parser import ResumeParser
from jobhunter.application.use_cases.profile_intake import ProfileIntakeService
from jobhunter.domain.profile import ParsedResume, ProfileInput
from jobhunter.infrastructure.db.session import get_session
from jobhunter.infrastructure.repositories.user_profile import (
    SQLAlchemyUserProfileRepository,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _get_service(session: AsyncSession = Depends(get_session)) -> ProfileIntakeService:  # noqa: B008
    repo = SQLAlchemyUserProfileRepository(session)
    return ProfileIntakeService(user_profile_repo=repo, session=session)


def _get_parser() -> ResumeParser:
    from jobhunter.adapters.llm.groq_client import GroqLlmClient, UsageTracker
    from jobhunter.adapters.parsing.llm_resume_parser import LlmResumeParser
    from jobhunter.config import get_settings

    settings = get_settings()
    tracker = UsageTracker(settings.llm_daily_call_cap)
    llm = GroqLlmClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
        usage_tracker=tracker,
    )
    return LlmResumeParser(llm=llm)


@router.post("", status_code=201)
async def create_profile(
    data: ProfileInput,
    service: ProfileIntakeService = Depends(_get_service),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, str]:
    profile_id = await service.create_or_update_profile(data)
    await session.commit()
    return {"id": str(profile_id)}


@router.get("/{profile_id}")
async def get_profile(
    profile_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, object]:
    repo = SQLAlchemyUserProfileRepository(session)
    profile = await repo.get_with_children(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _serialize_profile(profile)


@router.post("/ingest-resume")
async def ingest_resume(
    file: UploadFile,
    service: ProfileIntakeService = Depends(_get_service),  # noqa: B008
    parser: ResumeParser = Depends(_get_parser),  # noqa: B008
) -> ParsedResume:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename required")
    content = await file.read()
    return await service.ingest_resume(content, file.filename, parser)


def _serialize_profile(profile: object) -> dict[str, object]:
    from jobhunter.infrastructure.db.models import UserProfile

    p: UserProfile = profile  # type: ignore[assignment]
    return {
        "id": str(p.id),
        "full_name": p.full_name,
        "email": p.email,
        "phone": p.phone,
        "location": p.location,
        "headline": p.headline,
        "summary": p.summary,
        "github_url": p.github_url,
        "linkedin_url": p.linkedin_url,
        "website_url": p.website_url,
        "portfolio_url": p.portfolio_url,
        "visa_status": p.visa_status,
        "salary_min": p.salary_min,
        "salary_max": p.salary_max,
        "salary_currency": p.salary_currency,
        "availability": p.availability,
        "writing_style": p.writing_style,
        "remote_preference": p.remote_preference,
        "employment_types": p.employment_types,
        "languages": p.languages,
        "keywords": p.keywords,
        "preferred_locations": p.preferred_locations,
        "preferred_industries": p.preferred_industries,
        "work_experiences": [
            {
                "company_name": we.company_name,
                "title": we.title,
                "location": we.location,
                "start_date": str(we.start_date),
                "end_date": str(we.end_date) if we.end_date else None,
                "is_current": we.is_current,
                "description": we.description,
                "achievements": we.achievements,
                "technologies": we.technologies,
            }
            for we in p.work_experiences
        ],
        "educations": [
            {
                "institution": ed.institution,
                "degree": ed.degree,
                "field_of_study": ed.field_of_study,
                "start_date": str(ed.start_date),
                "end_date": str(ed.end_date) if ed.end_date else None,
                "gpa": ed.gpa,
            }
            for ed in p.educations
        ],
        "projects": [
            {
                "name": proj.name,
                "description": proj.description,
                "url": proj.url,
                "technologies": proj.technologies,
                "highlights": proj.highlights,
            }
            for proj in p.projects
        ],
        "certifications": [
            {
                "name": cert.name,
                "issuer": cert.issuer,
                "issue_date": str(cert.issue_date) if cert.issue_date else None,
                "expiry_date": str(cert.expiry_date) if cert.expiry_date else None,
                "credential_url": cert.credential_url,
            }
            for cert in p.certifications
        ],
        "skills": [
            {
                "name": sk.name,
                "category": sk.category,
                "proficiency": sk.proficiency,
            }
            for sk in p.skills
        ],
    }
