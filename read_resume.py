from sqlalchemy import create_engine, text
import json
e = create_engine("postgresql+psycopg2://jobhunter:jobhunter@localhost:5433/jobhunter")
c = e.connect()
r = c.execute(text("SELECT canonical_json FROM resume_versions ORDER BY created_at DESC LIMIT 1")).scalar()
data = r if isinstance(r, dict) else json.loads(r)
print("=== EXPERIENCES ===")
for exp in data.get("experiences", []):
    print(f"  {exp.get('title', '?')} at {exp.get('company', '?')}")
    for b in exp.get("bullets", []):
        print(f"    - {b}")
print(f"\n=== PROJECTS ===")
for p in data.get("projects", []):
    print(f"  {p}")
print(f"\n=== SKILLS ===")
for s in data.get("skills", []):
    if isinstance(s, dict):
        print(f"  {s.get('category','?')}: {s.get('skills', [])}")
