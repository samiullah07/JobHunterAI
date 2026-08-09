import re
files = [
    ("SCORER", "src/jobhunter/adapters/scoring/llm_job_scorer.py"),
    ("RESUME GEN", "src/jobhunter/adapters/generation/llm_resume_generator.py"),
    ("COVER GEN", "src/jobhunter/adapters/generation/llm_cover_letter_generator.py"),
]
for label, path in files:
    content = open(path, encoding="utf-8").read()
    lines = content.splitlines()
    print(f"\n=== {label} ({path}) ===")
    # Find system prompt
    for i, l in enumerate(lines):
        if "SYSTEM" in l.upper() or "system" in l or "description" in l.lower() and "job" in l.lower():
            print(f"  {i+1}: {l.strip()[:100]}")
    # Find where job data enters the prompt
    for i, l in enumerate(lines):
        if "description_raw" in l or "description_parsed" in l or "job.title" in l or "job.description" in l:
            print(f"  {i+1}: {l.strip()[:100]}")
