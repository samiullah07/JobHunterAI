"""Seed ONE fully-populated demo application in READY_FOR_REVIEW status.

Idempotent: if demo@jobhunter.local profile exists, wipes its downstream rows
and re-creates everything fresh.

Run: `uv run python scripts/seed_demo.py`
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

DEMO_EMAIL = "demo@jobhunter.local"
DEMO_COMPANY = "TechCo"
STORAGE_DIR = Path("./storage")


async def main() -> None:
    from sqlalchemy import delete, select, text
    from sqlalchemy.ext.asyncio import AsyncSession

    from jobhunter.infrastructure.db.models import (
        Application,
        ApplicationAnswer,
        Company,
        CoverLetterVersion,
        Education,
        Job,
        MatchScore,
        Project,
        ResumeVersion,
        Screenshot,
        Skill,
        UserProfile,
        WorkExperience,
    )
    from jobhunter.infrastructure.db.unit_of_work import unit_of_work

    async with unit_of_work() as session:
        session: AsyncSession  # type: ignore[no-redef]

        # ── Idempotent cleanup ──────────────────────────────────────────
        existing = (
            await session.execute(
                select(UserProfile).where(UserProfile.email == DEMO_EMAIL)
            )
        ).scalar_one_or_none()

        if existing:
            # Delete applications (cascades answers, screenshots)
            await session.execute(
                delete(Application).where(Application.profile_id == existing.id)
            )
            await session.execute(
                delete(MatchScore).where(MatchScore.profile_id == existing.id)
            )
            await session.execute(
                delete(ResumeVersion).where(ResumeVersion.profile_id == existing.id)
            )
            await session.execute(
                delete(CoverLetterVersion).where(
                    CoverLetterVersion.profile_id == existing.id
                )
            )
            await session.execute(
                delete(UserProfile).where(UserProfile.id == existing.id)
            )
            await session.flush()
            print(f"Cleaned up existing demo profile {existing.id}")

        # Clean up demo company/job too
        demo_company = (
            await session.execute(
                select(Company).where(Company.name == DEMO_COMPANY)
            )
        ).scalar_one_or_none()
        if demo_company:
            await session.execute(
                delete(Job).where(Job.company_id == demo_company.id)
            )
            await session.execute(
                delete(Company).where(Company.id == demo_company.id)
            )
            await session.flush()
            print(f"Cleaned up existing demo company {demo_company.id}")

        # ── 1. UserProfile with children ────────────────────────────────
        profile = UserProfile(
            full_name="Alex Chen",
            email=DEMO_EMAIL,
            phone="+1-555-987-6543",
            location="San Francisco, CA",
            headline="Senior Backend Engineer | Python, FastAPI, PostgreSQL",
            summary=(
                "Backend engineer with 6 years of experience building scalable "
                "microservices and data pipelines. Strong focus on API design, "
                "observability, and developer experience."
            ),
            github_url="https://github.com/alexchen-demo",
            linkedin_url="https://linkedin.com/in/alexchen-demo",
            visa_status="US Citizen",
            salary_min=140000,
            salary_max=180000,
            salary_currency="USD",
            availability="2 weeks notice",
            languages=["English", "Mandarin"],
            keywords=["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"],
        )
        session.add(profile)
        await session.flush()

        # Work experiences
        we1 = WorkExperience(
            profile_id=profile.id,
            company_name="Acme Corp",
            title="Senior Backend Engineer",
            location="San Francisco, CA (Remote)",
            start_date=date(2021, 3, 1),
            is_current=True,
            description="Lead backend engineer for the payments platform.",
            achievements=[
                "Reduced P95 latency from 800ms to 120ms by redesigning the caching layer",
                "Built event-driven architecture handling 50k events/sec with Kafka + FastAPI",
                "Mentored 3 junior engineers; introduced code review standards",
            ],
            technologies=["Python", "FastAPI", "PostgreSQL", "Redis", "Kafka", "Docker"],
        )
        we2 = WorkExperience(
            profile_id=profile.id,
            company_name="StartupCo",
            title="Backend Engineer",
            location="New York, NY",
            start_date=date(2018, 6, 15),
            end_date=date(2021, 2, 28),
            is_current=False,
            description="Full-stack engineer for B2B SaaS platform.",
            achievements=[
                "Designed and shipped the REST API serving 200+ enterprise clients",
                "Migrated legacy Django monolith to FastAPI microservices (40% throughput gain)",
                "Implemented CI/CD pipelines reducing deploy time from 45min to 8min",
            ],
            technologies=["Python", "Django", "FastAPI", "PostgreSQL", "AWS", "Terraform"],
        )
        session.add_all([we1, we2])

        # Education
        edu = Education(
            profile_id=profile.id,
            institution="University of California, Berkeley",
            degree="B.S. Computer Science",
            field_of_study="Computer Science",
            start_date=date(2014, 8, 20),
            end_date=date(2018, 5, 15),
            gpa=3.7,
        )
        session.add(edu)

        # Skills
        skills = [
            Skill(
                profile_id=profile.id, name="Python",
                category="Language", proficiency="Expert",
            ),
            Skill(
                profile_id=profile.id, name="PostgreSQL",
                category="Database", proficiency="Advanced",
            ),
            Skill(
                profile_id=profile.id, name="FastAPI",
                category="Framework", proficiency="Expert",
            ),
            Skill(
                profile_id=profile.id, name="Docker",
                category="DevOps", proficiency="Advanced",
            ),
        ]
        session.add_all(skills)

        # Project
        proj = Project(
            profile_id=profile.id,
            name="fastapi-events",
            description="Open-source event-driven middleware for FastAPI applications.",
            url="https://github.com/alexchen-demo/fastapi-events",
            technologies=["Python", "FastAPI", "Redis", "asyncio"],
            highlights=[
                "1.2k GitHub stars",
                "Used in production by 3 companies",
                "Async-first design with zero blocking I/O",
            ],
        )
        session.add(proj)
        await session.flush()

        # ── 2. Company + Job ────────────────────────────────────────────
        company = Company(
            name=DEMO_COMPANY,
            website="https://techco.example.com",
            description="Mid-stage startup building developer infrastructure.",
            is_preferred=True,
        )
        session.add(company)
        await session.flush()

        # Use text() INSERT to bypass SQLAlchemy Enum name/value mismatch with native enums
        job_id = uuid.uuid4()
        job_desc = (
            "We're looking for a Backend Developer to join our platform team. "
            "You'll design and build APIs, optimize database queries, and ship "
            "features that serve thousands of developers daily.\n\n"
            "Requirements:\n"
            "- 4+ years Python backend experience\n"
            "- Strong PostgreSQL and query optimization skills\n"
            "- Experience with FastAPI or similar async frameworks\n"
            "- Familiarity with Docker and container orchestration\n"
            "- Excellent communication and ownership mindset\n\n"
            "Nice to have:\n"
            "- Experience with event-driven architectures (Kafka, RabbitMQ)\n"
            "- Contributions to open-source projects\n"
            "- Experience scaling services to high throughput"
        )
        await session.execute(
            text("""
                INSERT INTO jobs (id, source, external_id, url, title, company_id,
                    company_name, location, salary_min, salary_max, salary_currency,
                    description_raw, posted_at, fetched_at)
                VALUES (:id, 'COMPANY_SITE', :external_id, :url, :title, :company_id,
                    :company_name, :location, :salary_min, :salary_max, :salary_currency,
                    :description_raw, :posted_at, :fetched_at)
            """),
            {
                "id": job_id,
                "external_id": f"demo-{uuid.uuid4().hex[:8]}",
                "url": "https://techco.example.com/careers/backend-dev",
                "title": "Backend Developer",
                "company_id": company.id,
                "company_name": DEMO_COMPANY,
                "location": "Remote (US)",
                "salary_min": 150000,
                "salary_max": 190000,
                "salary_currency": "USD",
                "description_raw": job_desc,
                "posted_at": datetime(2026, 7, 15, tzinfo=UTC),
                "fetched_at": datetime.now(UTC),
            },
        )

        # ── 3. MatchScore ───────────────────────────────────────────────
        match = MatchScore(
            job_id=job_id,
            profile_id=profile.id,
            overall=0.87,
            components={
                "skills": 0.92,
                "experience": 0.88,
                "location": 1.0,
                "salary": 0.85,
                "visa": 1.0,
                "remote": 1.0,
                "tech_stack": 0.90,
                "industry": 0.75,
                "culture": 0.70,
                "growth": 0.80,
            },
            rationale=(
                "Strong match: expert Python/FastAPI/PostgreSQL aligns with core requirements. "
                "6 years backend experience exceeds the 4-year minimum. Remote-first preference "
                "matches. Salary range overlaps. Open-source project is a bonus signal."
            ),
            passed_prefilter=True,
            similarity=0.84,
        )
        session.add(match)
        await session.flush()

        # ── 4. ResumeVersion ────────────────────────────────────────────
        canonical_json = {
            "contact": {
                "name": "Alex Chen",
                "email": DEMO_EMAIL,
                "phone": "+1-555-987-6543",
                "location": "San Francisco, CA",
                "github": "https://github.com/alexchen-demo",
                "linkedin": "https://linkedin.com/in/alexchen-demo",
            },
            "summary": (
                "Senior Backend Engineer with 6 years building high-throughput Python "
                "services. Expert in FastAPI, PostgreSQL, and event-driven architectures. "
                "Proven track record of reducing latency 85% and scaling to 50k events/sec."
            ),
            "experience": [
                {
                    "title": "Senior Backend Engineer",
                    "company": "Acme Corp",
                    "dates": "Mar 2021 – Present",
                    "bullets": [
                        "Reduced P95 latency from 800ms to 120ms"
                        " by redesigning the caching layer with Redis",
                        "Architected event-driven system handling"
                        " 50k events/sec using Kafka + FastAPI",
                        "Mentored 3 junior engineers"
                        " and established code review standards",
                    ],
                },
                {
                    "title": "Backend Engineer",
                    "company": "StartupCo",
                    "dates": "Jun 2018 – Feb 2021",
                    "bullets": [
                        "Designed REST API serving 200+"
                        " enterprise clients with 99.9% uptime",
                        "Led migration from Django monolith to"
                        " FastAPI microservices (40% throughput gain)",
                        "Implemented CI/CD reducing deploy"
                        " time from 45min to 8min",
                    ],
                },
            ],
            "education": [
                {
                    "degree": "B.S. Computer Science",
                    "institution": "UC Berkeley",
                    "dates": "2014 – 2018",
                    "gpa": "3.7",
                },
            ],
            "skills": {
                "Languages": ["Python", "SQL", "Go"],
                "Frameworks": ["FastAPI", "Django", "asyncio"],
                "Databases": ["PostgreSQL", "Redis", "Kafka"],
                "DevOps": ["Docker", "Kubernetes", "Terraform", "GitHub Actions"],
            },
            "fabrication_report": {"is_clean": True, "violations": []},
        }

        resume_version = ResumeVersion(
            profile_id=profile.id,
            job_id=job_id,
            version_label="Tailored for TechCo Backend Developer",
            canonical_json=canonical_json,
            storage_keys={"json": "resumes/demo/resume.json", "markdown": "resumes/demo/resume.md"},
        )
        session.add(resume_version)
        await session.flush()

        # ── 5. CoverLetterVersion ──────────────────────────────────────
        cover_body = (
            "Dear TechCo Hiring Team,\n\n"
            "I'm excited to apply for the Backend Developer role. With 6 years of "
            "Python backend experience — including building event-driven systems at "
            "Acme Corp that handle 50k events/sec — I'm confident I can contribute "
            "immediately to your platform team.\n\n"
            "Your requirements align closely with my daily work: I've spent the last "
            "3 years designing FastAPI services backed by PostgreSQL, optimizing queries "
            "that serve enterprise clients at scale, and containerizing everything with "
            "Docker. My open-source project fastapi-events (1.2k stars) demonstrates my "
            "commitment to the async Python ecosystem.\n\n"
            "I'm particularly drawn to TechCo's mission of building developer "
            "infrastructure — it's the kind of tooling I love both building and using. "
            "I'd welcome the chance to discuss how my experience scaling payments systems "
            "translates to your platform challenges.\n\n"
            "Best regards,\n"
            "Alex Chen"
        )

        cover_letter = CoverLetterVersion(
            profile_id=profile.id,
            job_id=job_id,
            version_label="Cover letter for TechCo Backend Developer",
            body_markdown=cover_body,
            storage_keys={"markdown": "cover_letters/demo/letter.md"},
        )
        session.add(cover_letter)
        await session.flush()

        # ── 6. Application (READY_FOR_REVIEW) ──────────────────────────
        app_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO applications (id, job_id, profile_id, resume_version_id,
                    cover_letter_version_id, status, notes)
                VALUES (:id, :job_id, :profile_id, :resume_version_id,
                    :cover_letter_version_id, 'READY_FOR_REVIEW', :notes)
            """),
            {
                "id": app_id,
                "job_id": job_id,
                "profile_id": profile.id,
                "resume_version_id": resume_version.id,
                "cover_letter_version_id": cover_letter.id,
                "notes": "Demo application seeded for M9 review UI testing.",
            },
        )

        # ── 7. ApplicationAnswers (what build_review_view reads) ────────
        answers = [
            ApplicationAnswer(
                application_id=app_id,
                question="Full Name",
                value="Alex Chen",
                source="profile.full_name",
            ),
            ApplicationAnswer(
                application_id=app_id,
                question="Email",
                value=DEMO_EMAIL,
                source="profile.email",
            ),
            ApplicationAnswer(
                application_id=app_id,
                question="Phone",
                value="+1-555-987-6543",
                source="profile.phone",
            ),
            ApplicationAnswer(
                application_id=app_id,
                question="Years of Experience",
                value="6",
                source="profile.work_experiences.duration",
            ),
            ApplicationAnswer(
                application_id=app_id,
                question="Work Authorization",
                value="US Citizen — no sponsorship needed",
                source="profile.visa_status",
            ),
            ApplicationAnswer(
                application_id=app_id,
                question="Earliest Start Date",
                value="2 weeks from offer",
                source="profile.availability",
            ),
        ]
        session.add_all(answers)

        # ── 8. Screenshots (placeholder PNGs) ──────────────────────────
        screenshot_dir = STORAGE_DIR / "screenshots" / "demo"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal 1x1 red PNG (67 bytes)
        minimal_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        for step in ("page1_filled", "page2_filled"):
            key = f"screenshots/demo/{step}.png"
            (STORAGE_DIR / key).parent.mkdir(parents=True, exist_ok=True)
            (STORAGE_DIR / key).write_bytes(minimal_png)

            screenshot = Screenshot(
                application_id=app_id,
                step_label=step,
                storage_key=key,
                is_final=(step == "page2_filled"),
            )
            session.add(screenshot)

        await session.flush()

        # ── Done ────────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print("DEMO SEED COMPLETE")
        print(f"{'='*60}")
        print(f"  Profile:     {profile.id} ({profile.full_name})")
        print(f"  Company:     {company.id} ({company.name})")
        print(f"  Job:         {job_id} (Backend Developer)")
        print(f"  MatchScore:  {match.overall:.0%}")
        print(f"  Resume:      {resume_version.id}")
        print(f"  Cover:       {cover_letter.id}")
        print(f"  Application: {app_id} [status=ready_for_review]")
        print(f"  Answers:     {len(answers)}")
        print("  Screenshots: 2")
        print(f"{'='*60}")
        print("\nThe review UI should now show this application in the queue.")
        print("Run: uv run streamlit run frontend/review_app.py")


if __name__ == "__main__":
    asyncio.run(main())
