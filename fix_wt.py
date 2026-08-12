path = "src/jobhunter/domain/scoring.py"
content = open(path, encoding="utf-8").read()

replacements = [
    ("    skills: float = 0.20", "    skills: float = 0.25"),
    ("    salary: float = 0.10", "    salary: float = 0.05"),
    ("    visa: float = 0.05", "    visa: float = 0.03"),
    ("    tech_stack: float = 0.15", "    tech_stack: float = 0.25"),
    ("    culture: float = 0.05", "    culture: float = 0.02"),
    ("    growth: float = 0.10", "    growth: float = 0.05"),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"  {old.strip()} -> {new.strip()}")
    else:
        print(f"  NOT FOUND: {old.strip()}")

open(path, "w", encoding="utf-8").write(content)

# Verify sum = 1.0
vals = [0.25, 0.15, 0.05, 0.05, 0.03, 0.10, 0.25, 0.05, 0.02, 0.05]
print(f"\nNew weights sum: {sum(vals):.2f}")
