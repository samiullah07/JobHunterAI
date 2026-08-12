path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

old = "                if isinstance(proj, dict):\n                    proj_name = proj.get('name')"
new = "                if isinstance(proj, dict):\n                    proj_name = proj.get('name')\n                elif hasattr(proj, 'name'):\n                    proj_name = proj.name"

# Actually, simpler fix: handle both dict and object in one block
content = content.replace(
    """        if parsed.projects:
            for proj in parsed.projects:
                if isinstance(proj, dict):
                    proj_name = proj.get('name') or proj.get('title') or 'Unnamed Project'
                    proj_url = proj.get('url') or proj.get('github') or proj.get('link') or None
                    if proj_url and not proj_url.startswith('http'):
                        proj_url = 'https://' + proj_url
                    proj_tech = proj.get('technologies') or proj.get('tech_stack') or None
                    session.add(Project(
                        profile_id=profile.id,
                        name=proj_name[:300],
                        description=proj.get('description') or None,
                        url=proj_url,
                        technologies=proj_tech if isinstance(proj_tech, list) else None,
                    ))
                    proj_count += 1""",
    """        if parsed.projects:
            for proj in parsed.projects:
                # Handle both dict and Pydantic model objects
                if isinstance(proj, dict):
                    p_name = proj.get('name') or proj.get('title') or 'Unnamed Project'
                    p_url = proj.get('url') or proj.get('github') or None
                    p_desc = proj.get('description') or None
                    p_tech = proj.get('technologies') or None
                else:
                    p_name = getattr(proj, 'name', None) or getattr(proj, 'title', None) or 'Unnamed Project'
                    p_url = getattr(proj, 'url', None) or getattr(proj, 'github', None) or None
                    p_desc = getattr(proj, 'description', None)
                    p_tech = getattr(proj, 'technologies', None)
                if p_url and not str(p_url).startswith('http'):
                    p_url = 'https://' + str(p_url)
                session.add(Project(
                    profile_id=profile.id,
                    name=str(p_name)[:300],
                    description=p_desc,
                    url=p_url,
                    technologies=p_tech if isinstance(p_tech, list) else None,
                ))
                proj_count += 1"""
)

open(path, "w", encoding="utf-8").write(content)
print("FIXED: handle both dict and Pydantic model for projects")
