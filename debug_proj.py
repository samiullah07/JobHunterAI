path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

old = "        # Insert projects\n        proj_count = 0"
new = """        # Insert projects
        import logging
        logging.warning(f"PROJECTS DEBUG: type={type(parsed.projects)}, value={str(parsed.projects)[:500]}")
        proj_count = 0"""

if old in content:
    content = content.replace(old, new)
    open(path, "w", encoding="utf-8").write(content)
    print("ADDED: projects debug logging")
else:
    print("FAILED: projects insertion block not found - checking if it exists")
    print("has 'Insert projects':", "Insert projects" in content)
    print("has 'proj_count':", "proj_count" in content)
