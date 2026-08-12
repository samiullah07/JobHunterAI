from sqlalchemy import create_engine, text
e = create_engine("postgresql+psycopg2://jobhunter:jobhunter@localhost:5433/jobhunter")
c = e.connect()

# Profile completeness
profile = c.execute(text("""
    SELECT full_name, email, phone, location, summary, 
           visa_status, salary_min, remote_preference,
           linkedin_url, github_url
    FROM user_profiles LIMIT 1
""")).fetchone()
print("=== PROFILE COMPLETENESS ===")
filled = sum(1 for v in profile if v is not None)
print(f"Fields filled: {filled}/10")
for name, val in zip(['name','email','phone','location','summary','visa','salary_min','remote','linkedin','github'], profile):
    print(f"  {name}: {'SET' if val else 'EMPTY'}")

# Skills, experiences, educations
skills = c.execute(text("SELECT COUNT(*) FROM skills")).scalar()
exps = c.execute(text("SELECT COUNT(*) FROM work_experiences")).scalar()
edus = c.execute(text("SELECT COUNT(*) FROM educations")).scalar()
projs = c.execute(text("SELECT COUNT(*) FROM projects")).scalar()
print(f"\nSkills: {skills}, Experiences: {exps}, Educations: {edus}, Projects: {projs}")

# Job relevance
jobs = c.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
scored = c.execute(text("SELECT COUNT(*) FROM match_scores")).scalar()
apps = c.execute(text("SELECT COUNT(*) FROM applications")).scalar()
approved = c.execute(text("SELECT COUNT(*) FROM applications WHERE status = 'APPROVED'")).scalar()
print(f"\nJobs: {jobs}, Scored: {scored}, Applications: {apps}, Approved: {approved}")

# Resume versions
resumes = c.execute(text("SELECT COUNT(*) FROM resume_versions")).scalar()
covers = c.execute(text("SELECT COUNT(*) FROM cover_letter_versions")).scalar()
print(f"Resume versions: {resumes}, Cover letters: {covers}")
