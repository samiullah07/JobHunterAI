from sqlalchemy import create_engine, text
e = create_engine("postgresql+psycopg2://jobhunter:jobhunter@localhost:5433/jobhunter")
c = e.connect()
ms = c.execute(text("SELECT COUNT(*) FROM match_scores")).scalar()
rv = c.execute(text("SELECT COUNT(*) FROM resume_versions")).scalar()
apps = c.execute(text("SELECT COUNT(*) FROM applications")).scalar()
jobs = c.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
print(f"match_scores: {ms}, resume_versions: {rv}, applications: {apps}, jobs: {jobs}")
