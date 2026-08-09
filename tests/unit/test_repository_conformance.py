"""Static + runtime conformance: every impl satisfies its Protocol.

The TYPE_CHECKING block is verified by `mypy tests/` — if any impl
drifts from its Protocol, mypy will error on the typed assignment.
The runtime test simply confirms the classes are importable.
"""

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.application.repositories.application import ApplicationRepository
    from jobhunter.application.repositories.ats_report import AtsReportRepository
    from jobhunter.application.repositories.company import CompanyRepository
    from jobhunter.application.repositories.cover_letter_version import (
        CoverLetterVersionRepository,
    )
    from jobhunter.application.repositories.job import JobRepository
    from jobhunter.application.repositories.match_score import MatchScoreRepository
    from jobhunter.application.repositories.resume_version import ResumeVersionRepository
    from jobhunter.application.repositories.user_profile import UserProfileRepository
    from jobhunter.infrastructure.repositories.application import (
        SQLAlchemyApplicationRepository,
    )
    from jobhunter.infrastructure.repositories.ats_report import SQLAlchemyAtsReportRepository
    from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository
    from jobhunter.infrastructure.repositories.cover_letter_version import (
        SQLAlchemyCoverLetterVersionRepository,
    )
    from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
    from jobhunter.infrastructure.repositories.match_score import (
        SQLAlchemyMatchScoreRepository,
    )
    from jobhunter.infrastructure.repositories.resume_version import (
        SQLAlchemyResumeVersionRepository,
    )
    from jobhunter.infrastructure.repositories.user_profile import (
        SQLAlchemyUserProfileRepository,
    )

    # Static conformance checks — mypy errors here if impl diverges from Protocol.
    _session = cast("AsyncSession", None)
    _user_profile: UserProfileRepository = SQLAlchemyUserProfileRepository(_session)
    _company: CompanyRepository = SQLAlchemyCompanyRepository(_session)
    _job: JobRepository = SQLAlchemyJobRepository(_session)
    _match_score: MatchScoreRepository = SQLAlchemyMatchScoreRepository(_session)
    _application: ApplicationRepository = SQLAlchemyApplicationRepository(_session)
    _resume_version: ResumeVersionRepository = SQLAlchemyResumeVersionRepository(_session)
    _cover_letter: CoverLetterVersionRepository = SQLAlchemyCoverLetterVersionRepository(_session)
    _ats_report: AtsReportRepository = SQLAlchemyAtsReportRepository(_session)


def test_all_repository_impls_importable() -> None:
    """Runtime smoke test — confirms all impl classes can be imported."""
    from jobhunter.infrastructure.repositories.application import (
        SQLAlchemyApplicationRepository,
    )
    from jobhunter.infrastructure.repositories.ats_report import SQLAlchemyAtsReportRepository
    from jobhunter.infrastructure.repositories.company import SQLAlchemyCompanyRepository
    from jobhunter.infrastructure.repositories.cover_letter_version import (
        SQLAlchemyCoverLetterVersionRepository,
    )
    from jobhunter.infrastructure.repositories.job import SQLAlchemyJobRepository
    from jobhunter.infrastructure.repositories.match_score import (
        SQLAlchemyMatchScoreRepository,
    )
    from jobhunter.infrastructure.repositories.resume_version import (
        SQLAlchemyResumeVersionRepository,
    )
    from jobhunter.infrastructure.repositories.user_profile import (
        SQLAlchemyUserProfileRepository,
    )

    impls = [
        SQLAlchemyUserProfileRepository,
        SQLAlchemyCompanyRepository,
        SQLAlchemyJobRepository,
        SQLAlchemyMatchScoreRepository,
        SQLAlchemyApplicationRepository,
        SQLAlchemyResumeVersionRepository,
        SQLAlchemyCoverLetterVersionRepository,
        SQLAlchemyAtsReportRepository,
    ]
    assert len(impls) == 8
