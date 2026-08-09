---
name: ats-resume-writing
description: Rules for generating and optimizing ATS-friendly resumes and cover letters from verified profile data. Consult whenever writing the resume-generation, cover-letter, or ATS-optimization agents or their prompts.
---

# ATS Resume & Cover-Letter Rules

Integrity (non-negotiable):
- NEVER fabricate experience, dates, titles, skills, or metrics. Use only verified UserProfile data.
- If a job needs something the profile lacks, surface the gap for the human — do not invent it.

ATS optimization:
- Parse the job description into: hard skills, responsibilities, required quals, preferred quals, soft skills.
- Mirror the job's exact keyword phrasing where the profile truthfully supports it.
- Single-column, standard section headings (Experience, Education, Skills, Projects). No tables, text boxes, images, headers/footers, or graphics that break ATS parsers.
- Standard fonts, clear date formats, reverse-chronological.
- Prioritize matching experience to the top; quantify achievements with real numbers from the profile.

Outputs (produce all four, version them):
- JSON — canonical structured resume (source of truth).
- Markdown — human-readable.
- DOCX — via python-docx.
- PDF — render an HTML/Jinja template and print with Playwright page.pdf().

Cover letters: company-specific and role-specific; why-company, why-role, one relevant achievement, call to action. Natural voice; avoid generic AI filler. Store a version per application.

Always emit an ATS analysis report: matched vs missing keywords, a score, and concrete suggestions.