path = "src/jobhunter/adapters/rendering/pdf_resume.py"
content = open(path, encoding="utf-8").read()

# Find the experience section and add a projects fallback
old_pdf = """    # Experience
    experiences = resume_json.get('experiences', [])
    if experiences:
        elements.append(Paragraph('EXPERIENCE', section_style))"""

new_pdf = """    # Experience (or Projects if no traditional experience)
    experiences = resume_json.get('experiences', [])
    projects_as_exp = resume_json.get('projects', []) if not experiences else []
    if experiences:
        elements.append(Paragraph('EXPERIENCE', section_style))"""

if old_pdf in content:
    content = content.replace(old_pdf, new_pdf)
    
    # Add projects-as-experience rendering after the experiences loop
    old_after_exp = """    # Education"""
    new_after_exp = """    # Projects as Experience (when no traditional employment)
    if projects_as_exp:
        elements.append(Paragraph('PROJECT EXPERIENCE', section_style))
        for proj in projects_as_exp:
            if isinstance(proj, dict):
                name = proj.get('name', '')
                desc = proj.get('description', '')
                url = proj.get('url', '')
                tech = proj.get('technologies', [])
                elements.append(Paragraph(f"<b>{name}</b>", job_title_style))
                if desc:
                    elements.append(Paragraph(str(desc), body_style))
                if url:
                    elements.append(Paragraph(f"Link: {url}", contact_style))
                if tech and isinstance(tech, list):
                    elements.append(Paragraph(f"<i>Technologies: {', '.join(str(t) for t in tech)}</i>", contact_style))

    # Education"""
    
    content = content.replace(old_after_exp, new_after_exp, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: PDF export includes projects as experience")
else:
    print("FAILED: PDF experience block not found")
