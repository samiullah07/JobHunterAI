path = "src/jobhunter/adapters/parsing/llm_resume_parser.py"
content = open(path, encoding="utf-8").read()

# Find the projects normalization section and add sub-object field mapping
old_projects = """    # Projects (aggressive fuzzy match)
    if "projects" not in d:
        for key in list(d.keys()):
            if "project" in key.lower():
                d["projects"] = d.pop(key)
                break"""

new_projects = """    # Projects (aggressive fuzzy match)
    if "projects" not in d:
        for key in list(d.keys()):
            if "project" in key.lower():
                d["projects"] = d.pop(key)
                break
    # Normalize project sub-objects
    if "projects" in d and isinstance(d["projects"], list):
        for proj in d["projects"]:
            if isinstance(proj, dict):
                # github/link -> url
                if "url" not in proj:
                    for url_key in ("github", "link", "repo", "github_url", "repo_url"):
                        if url_key in proj:
                            url = proj.pop(url_key)
                            if url and not str(url).startswith("http"):
                                url = "https://" + str(url)
                            proj["url"] = url
                            break
                # title -> name
                if "name" not in proj and "title" in proj:
                    proj["name"] = proj.pop("title")
                # tech_stack -> technologies
                if "technologies" not in proj and "tech_stack" in proj:
                    proj["technologies"] = proj.pop("tech_stack")
    elif "projects" in d and isinstance(d["projects"], dict):
        d["projects"] = [d["projects"]]"""

if old_projects in content:
    content = content.replace(old_projects, new_projects)
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: added project sub-object normalization (github->url, title->name)")
else:
    print("FAILED: projects block not found")
