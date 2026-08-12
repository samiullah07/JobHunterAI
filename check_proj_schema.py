from jobhunter.domain.profile import ParsedResume
import json

# What does ParsedResume expect for projects?
schema = ParsedResume.model_json_schema()
proj_schema = schema.get("properties", {}).get("projects", {})
print("=== ParsedResume.projects schema ===")
print(json.dumps(proj_schema, indent=2)[:500])

# Also check the sub-model if it exists
for key, val in schema.get("$defs", {}).items():
    if "project" in key.lower():
        print(f"\n=== {key} sub-model ===")
        print(json.dumps(val, indent=2)[:500])
