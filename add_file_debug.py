path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

old = "        import logging\n        logging.warning(f'PROJECTS DEBUG"
if old in content:
    content = content.replace(
        old,
        "        open('_proj_debug.txt','w').write(f'projects type={type(parsed.projects)}\\nprojects value={str(parsed.projects)[:1000]}\\neducations={str(parsed.educations)[:500]}')\n        import logging\n        logging.warning(f'PROJECTS DEBUG"
    )
    open(path, "w", encoding="utf-8").write(content)
    print("ADDED: file-based debug")
else:
    print("FAILED: debug line not found")
    print("Checking for proj_count:", "proj_count" in content)
    print("Checking for Insert projects:", "Insert projects" in content)
