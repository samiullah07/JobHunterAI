path = "src/jobhunter/adapters/generation/llm_resume_generator.py"
content = open(path, encoding="utf-8").read()

old_block = """    if profile.work_experiences:
        parts.append("\\nWork Experience:")
        for exp in profile.work_experiences:
            end = "present" if exp.is_current else str(exp.end_date or "?")
            parts.append(f"  {exp.title} @ {exp.company_name} ({exp.start_date} to {end})")
            if exp.description:
                parts.append(f"    Description: {exp.description}")
            if exp.achievements:
                for a in exp.achievements:
                    parts.append(f"    - {a}")
            if exp.technologies:
                parts.append(f"    Technologies: {', '.join(exp.technologies)}")

    if profile.educations:"""

new_block = """    if profile.work_experiences:
        parts.append("\\nWork Experience:")
        for exp in profile.work_experiences:
            end = "present" if exp.is_current else str(exp.end_date or "?")
            parts.append(f"  {exp.title} @ {exp.company_name} ({exp.start_date} to {end})")
            if exp.description:
                parts.append(f"    Description: {exp.description}")
            if exp.achievements:
                for a in exp.achievements:
                    parts.append(f"    - {a}")
            if exp.technologies:
                parts.append(f"    Technologies: {', '.join(exp.technologies)}")
    elif profile.projects:
        # No traditional work experience — promote projects as experience
        parts.append("\\nProject Experience (in lieu of traditional employment):")
        for proj in profile.projects:
            parts.append(f"  {proj.name}")
            if proj.description:
                parts.append(f"    {proj.description}")
            if proj.url:
                parts.append(f"    Link: {proj.url}")
            if proj.technologies:
                parts.append(f"    Technologies: {', '.join(proj.technologies)}")

    if profile.educations:"""

if old_block in content:
    content = content.replace(old_block, new_block)
    open(path, "w", encoding="utf-8").write(content)
    print("FIXED: projects promoted to experience when no work history exists")
else:
    print("FAILED: block not found")
