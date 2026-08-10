import asyncio
from jobhunter.infrastructure.db.unit_of_work import unit_of_work
from jobhunter.infrastructure.db.models import Job, UserProfile, ResumeVersion
from sqlalchemy import select, exists

async def test_fallback():
    async with unit_of_work() as session:
        # Check: does the fallback query find jobs?
        has_resume = exists(
            select(ResumeVersion.id).where(ResumeVersion.job_id == Job.id)
        )
        result = await session.execute(
            select(Job)
            .where(~has_resume)
            .order_by(Job.created_at.desc())
            .limit(5)
        )
        jobs = result.scalars().all()
        print(f"Jobs without resumes: {len(jobs)}")
        for j in jobs[:3]:
            print(f"  {j.title} at {j.company_name}")
        
        # Check: does profile exist?
        p_result = await session.execute(select(UserProfile.id).limit(1))
        p_id = p_result.scalar_one_or_none()
        print(f"Profile ID: {p_id}")
        
        if not jobs:
            print("BUG: No jobs without resumes found!")
        if not p_id:
            print("BUG: No profile found!")

asyncio.run(test_fallback())
