"""Profile intake use case — create/update profiles and ingest résumés.

The human-accept boundary: parsed résumé data is a PROPOSAL until
accept_parsed_resume is called. Only then does it become "verified" profile data.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from jobhunter.domain.profile import ParsedResume, ProfileInput
from jobhunter.infrastructure.db.models import (
    Certification,
    Education,
    Project,
    Skill,
    UserProfile,
    WorkExperience,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.application.ports.resume_parser import ResumeParser
    from jobhunter.application.repositories.user_profile import UserProfileRepository


class ProfileIntakeService:
    """Orchestrates profile creation, update, and résumé ingestion."""

    def __init__(
        self,
        user_profile_repo: UserProfileRepository,
        session: AsyncSession,
    ) -> None:
        self._repo = user_profile_repo
        self._session = session

    async def create_or_update_profile(self, data: ProfileInput) -> uuid.UUID:
        """Upsert a profile by email. Repositories flush; caller (UoW) commits."""
        existing = await self._repo.get_by_email(data.email)
        if existing is not None:
            loaded = await self._repo.get_with_children(existing.id)
            assert loaded is not None
            return await self._update_profile(loaded, data)
        return await self._create_profile(data)

    async def ingest_resume(
        self, file_bytes: bytes, filename: str, parser: ResumeParser
    ) -> ParsedResume:
        """Parse a résumé file — returns a PROPOSAL, does NOT persist anything."""
        return await parser.parse(file_bytes, filename)

    async def accept_parsed_resume(
        self, parsed: ParsedResume, overrides: ProfileInput | None = None
    ) -> uuid.UUID:
        """Merge accepted parsed data (+ optional overrides) into a persisted profile.

        Overrides win over parsed values. This is the human-in-the-loop boundary:
        parsed data only becomes "verified" here.
        """
        merged = self._merge_parsed_with_overrides(parsed, overrides)
        return await self.create_or_update_profile(merged)

    def _merge_parsed_with_overrides(
        self, parsed: ParsedResume, overrides: ProfileInput | None
    ) -> ProfileInput:
        """Build a ProfileInput from parsed data, with overrides winning on conflicts.

        Dumps parsed data to a plain dict (Python-native types preserved) so that
        strict ProfileInput validation accepts them without coercion issues.
        """
        parsed_dump = parsed.model_dump(
            exclude_none=True, exclude={"source_filename", "confidence"}
        )

        if overrides is not None:
            override_dump = overrides.model_dump(exclude_none=True)
            parsed_dump.update(override_dump)

        return ProfileInput.model_validate(parsed_dump)

    async def _create_profile(self, data: ProfileInput) -> uuid.UUID:
        profile = UserProfile(
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            location=data.location,
            headline=data.headline,
            summary=data.summary,
            github_url=data.github_url,
            linkedin_url=data.linkedin_url,
            website_url=data.website_url,
            portfolio_url=data.portfolio_url,
            visa_status=data.visa_status,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_currency=data.salary_currency,
            availability=data.availability,
            writing_style=data.writing_style,
            preferred_locations=data.preferred_locations,
            remote_preference=data.remote_preference.value if data.remote_preference else None,
            employment_types=[e.value for e in data.employment_types]
            if data.employment_types
            else None,
            languages=data.languages,
            keywords=data.keywords,
            preferred_industries=data.preferred_industries,
        )
        self._add_children(profile, data)
        await self._repo.add(profile)
        return profile.id

    async def _update_profile(self, existing: UserProfile, data: ProfileInput) -> uuid.UUID:
        existing.full_name = data.full_name
        existing.email = data.email
        existing.phone = data.phone
        existing.location = data.location
        existing.headline = data.headline
        existing.summary = data.summary
        existing.github_url = data.github_url
        existing.linkedin_url = data.linkedin_url
        existing.website_url = data.website_url
        existing.portfolio_url = data.portfolio_url
        existing.visa_status = data.visa_status
        existing.salary_min = data.salary_min
        existing.salary_max = data.salary_max
        existing.salary_currency = data.salary_currency
        existing.availability = data.availability
        existing.writing_style = data.writing_style
        existing.preferred_locations = data.preferred_locations
        existing.remote_preference = (
            data.remote_preference.value if data.remote_preference else None
        )
        existing.employment_types = (
            [e.value for e in data.employment_types] if data.employment_types else None
        )
        existing.languages = data.languages
        existing.keywords = data.keywords
        existing.preferred_industries = data.preferred_industries

        # Replace children: delete old, add new
        existing.work_experiences.clear()
        existing.educations.clear()
        existing.projects.clear()
        existing.certifications.clear()
        existing.skills.clear()
        await self._session.flush()

        self._add_children(existing, data)
        await self._repo.update(existing)
        return existing.id

    def _add_children(self, profile: UserProfile, data: ProfileInput) -> None:
        if data.work_experiences:
            for we in data.work_experiences:
                profile.work_experiences.append(
                    WorkExperience(
                        company_name=we.company_name,
                        title=we.title,
                        location=we.location,
                        start_date=we.start_date,
                        end_date=we.end_date,
                        is_current=we.is_current,
                        description=we.description,
                        achievements=we.achievements,
                        technologies=we.technologies,
                    )
                )
        if data.educations:
            for ed in data.educations:
                profile.educations.append(
                    Education(
                        institution=ed.institution,
                        degree=ed.degree,
                        field_of_study=ed.field_of_study,
                        start_date=ed.start_date,
                        end_date=ed.end_date,
                        gpa=ed.gpa,
                    )
                )
        if data.projects:
            for proj in data.projects:
                profile.projects.append(
                    Project(
                        name=proj.name,
                        description=proj.description,
                        url=proj.url,
                        technologies=proj.technologies,
                        highlights=proj.highlights,
                    )
                )
        if data.certifications:
            for cert in data.certifications:
                profile.certifications.append(
                    Certification(
                        name=cert.name,
                        issuer=cert.issuer,
                        issue_date=cert.issue_date,
                        expiry_date=cert.expiry_date,
                        credential_url=cert.credential_url,
                    )
                )
        if data.skills:
            for sk in data.skills:
                profile.skills.append(
                    Skill(
                        name=sk.name,
                        category=sk.category,
                        proficiency=sk.proficiency,
                    )
                )
