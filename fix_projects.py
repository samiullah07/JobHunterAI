path = "frontend/pages/1_My_Profile.py"
content = open(path, encoding="utf-8").read()

# Fix 1: Add Project to imports
old_import = "Application, MatchScore, ResumeVersion, CoverLetterVersion,"
new_import = "Application, MatchScore, ResumeVersion, CoverLetterVersion, Project,"
if old_import in content:
    content = content.replace(old_import, new_import, 1)
    print("FIXED: added Project to imports")
else:
    print("FAILED: import line not found")

# Fix 2: Add project deletion to the wipe block (before profile delete)
old_wipe = "            await session.execute(delete(Education).where(Education.profile_id == pid))"
new_wipe = """            await session.execute(delete(Education).where(Education.profile_id == pid))
            await session.execute(delete(Project).where(Project.profile_id == pid))"""
if old_wipe in content:
    content = content.replace(old_wipe, new_wipe)
    print("FIXED: added Project deletion to wipe block")
else:
    print("FAILED: wipe block not found")

# Fix 3: Add project insertion after education insertion
# Find the education insertion block's end and add projects after it
old_edu_end = """        await session.flush()
        return {"full_name": parsed.full_name, "skills_count": skills_count, "exp_count": exp_count}"""

new_edu_end = """        # Insert projects
        proj_count = 0
        if parsed.projects:
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
                    proj_count += 1

        await session.flush()
        return {"full_name": parsed.full_name, "skills_count": skills_count, "exp_count": exp_count, "proj_count": proj_count}"""

if old_edu_end in content:
    content = content.replace(old_edu_end, new_edu_end)
    print("FIXED: added project insertion")
else:
    print("FAILED: edu end block not found")

# Fix 4: Update the success message to show project count
old_success = '''st.success(f"Profile created from CV: {result['full_name']} - {result['skills_count']} skills, {result['exp_count']} experiences")'''
new_success = '''st.success(f"Profile created from CV: {result['full_name']} - {result['skills_count']} skills, {result.get('proj_count', 0)} projects, {result['exp_count']} experiences")'''
if old_success in content:
    content = content.replace(old_success, new_success)
    print("FIXED: updated success message to show project count")
else:
    print("FAILED: success message not found")

open(path, "w", encoding="utf-8").write(content)
