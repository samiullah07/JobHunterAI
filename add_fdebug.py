path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

old = '        logging.warning(f"PROJECTS DEBUG: type={type(parsed.projects)}, value={str(parsed.projects)[:500]}")'
new = '''        open("_proj_debug.txt", "w").write(f"projects type={type(parsed.projects)}\\nlen={len(parsed.projects) if parsed.projects else 0}\\nvalue={str(parsed.projects)[:1000]}")
        logging.warning(f"PROJECTS DEBUG: type={type(parsed.projects)}, value={str(parsed.projects)[:500]}")'''

if old in content:
    content = content.replace(old, new)
    open(path, "w", encoding="utf-8").write(content)
    print("ADDED file debug")
else:
    print("FAILED")
