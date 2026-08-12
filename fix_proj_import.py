path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

# Find the manual save function's import block and add Project
# The manual save imports are separate from the CV upload save
old = "Application, MatchScore, ResumeVersion, CoverLetterVersion,\n            )\n            from sqlalchemy import delete, select"
new = "Application, MatchScore, ResumeVersion, CoverLetterVersion, Project,\n            )\n            from sqlalchemy import delete, select"

# Try both possible locations (there may be two import blocks - one for CV upload, one for manual)
count = content.count(old)
if count > 0:
    content = content.replace(old, new)
    print(f"FIXED: added Project import ({count} locations)")
else:
    # Try alternate format
    old2 = "Application, MatchScore, ResumeVersion, CoverLetterVersion,"
    if old2 in content:
        content = content.replace(old2, "Application, MatchScore, ResumeVersion, CoverLetterVersion, Project,")
        print("FIXED: added Project to import (alternate format)")
    else:
        print("FAILED: import block not found")

open(path, "w", encoding="utf-8").write(content)
