path = "src/jobhunter/domain/scoring.py"
content = open(path, encoding="utf-8").read()

# Find the current default weights
old_weights = """'skills': 0.2, 'experience': 0.15, 'location': 0.05, 'salary': 0.1, 'visa': 0.05, 'remote': 0.1, 'tech_stack': 0.15, 'industry': 0.05, 'culture': 0.05, 'growth': 0.1"""

new_weights = """'skills': 0.25, 'experience': 0.15, 'location': 0.05, 'salary': 0.05, 'visa': 0.03, 'remote': 0.10, 'tech_stack': 0.25, 'industry': 0.05, 'culture': 0.02, 'growth': 0.05"""

if old_weights in content:
    content = content.replace(old_weights, new_weights)
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: reweighted to emphasize skills/tech_stack")
else:
    # Try to find it with different formatting
    import re
    lines = content.splitlines()
    for i, l in enumerate(lines):
        if "skills" in l and "0.2" in l and "experience" in l:
            print(f"Found weights at line {i+1}: {l.strip()[:100]}")
    print("FAILED: exact weight string not found - may need manual edit")
