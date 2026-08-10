path = "src/jobhunter/workers/generation.py"
content = open(path, encoding="utf-8").read()

old_block = """        # 1. Get top N matches (highest overall score, filtered to passed prefilter)
        result = await session.execute(
            select(MatchScore)
            .where(MatchScore.passed_prefilter == True)  # noqa: E712
            .order_by(MatchScore.overall.desc())
            .limit(limit)
        )
        matches = result.scalars().all()
        logger.info("top_matches_fetched", count=len(matches))

        generated = 0
        for match in matches:
            job = await session.get(Job, match.job_id)"""

new_block = """        # 1. Try match_scores first; fall back to newest jobs if no scores exist
        result = await session.execute(
            select(MatchScore)
            .where(MatchScore.passed_prefilter == True)  # noqa: E712
            .order_by(MatchScore.overall.desc())
            .limit(limit)
        )
        matches = result.scalars().all()
        logger.info("top_matches_fetched", count=len(matches))

        # Build list of (job, profile) pairs to generate for
        job_profile_pairs = []
        if matches:
            for match in matches:
                j = await session.get(Job, match.job_id)
                job_profile_pairs.append((j, match.profile_id))
        else:
            # Fallback: pick newest jobs that don't already have a resume
            logger.info("no_match_scores_found", fallback="newest_jobs")
            from sqlalchemy import and_, exists
            has_resume = exists(
                select(ResumeVersion.id).where(ResumeVersion.job_id == Job.id)
            )
            fallback_result = await session.execute(
                select(Job)
                .where(~has_resume)
                .order_by(Job.created_at.desc())
                .limit(limit)
            )
            fallback_jobs = fallback_result.scalars().all()
            # Get the single active profile
            p_result = await session.execute(select(UserProfile.id).limit(1))
            p_id = p_result.scalar_one_or_none()
            if p_id and fallback_jobs:
                for j in fallback_jobs:
                    job_profile_pairs.append((j, p_id))
            logger.info("fallback_jobs_selected", count=len(job_profile_pairs))

        generated = 0
        for job, profile_id in job_profile_pairs:"""

if old_block in content:
    content = content.replace(old_block, new_block)
    # Also fix the profile fetch — it used match.profile_id, now uses profile_id directly
    content = content.replace(
        "                .where(UserProfile.id == match.profile_id)",
        "                .where(UserProfile.id == profile_id)"
    )
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: added fallback job selection when no match_scores exist")
else:
    print("FAILED: block not found")
