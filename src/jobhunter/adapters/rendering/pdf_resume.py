"""Generate a professional PDF resume from canonical JSON using reportlab."""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable


def generate_resume_pdf(resume_json: dict) -> bytes:
    """Convert a canonical resume JSON dict to a formatted PDF.

    Returns PDF as bytes, ready for download.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    name_style = ParagraphStyle(
        'Name', parent=styles['Title'],
        fontSize=18, spaceAfter=2*mm, textColor=HexColor('#1a1a1a'),
    )
    contact_style = ParagraphStyle(
        'Contact', parent=styles['Normal'],
        fontSize=9, spaceAfter=4*mm, textColor=HexColor('#555555'),
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'],
        fontSize=12, spaceBefore=5*mm, spaceAfter=2*mm,
        textColor=HexColor('#2a5599'), borderWidth=0,
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=10, spaceAfter=2*mm, leading=14,
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=styles['Normal'],
        fontSize=10, leftIndent=10*mm, spaceAfter=1*mm, leading=13,
        bulletIndent=5*mm,
    )
    job_title_style = ParagraphStyle(
        'JobTitle', parent=styles['Normal'],
        fontSize=10, spaceAfter=1*mm, leading=13,
        textColor=HexColor('#1a1a1a'),
    )

    elements = []

    # Header: Name
    name = resume_json.get('full_name', 'Name Not Provided')
    elements.append(Paragraph(name, name_style))

    # Contact line
    contact_parts = []
    for field in ['email', 'phone', 'location']:
        val = resume_json.get(field)
        if val:
            contact_parts.append(str(val))
    if contact_parts:
        elements.append(Paragraph(' | '.join(contact_parts), contact_style))

    # Links line
    link_parts = []
    for field in ['linkedin_url', 'github_url']:
        val = resume_json.get(field)
        if val:
            link_parts.append(str(val))
    if link_parts:
        elements.append(Paragraph(' | '.join(link_parts), contact_style))

    # Divider
    elements.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#cccccc')))
    elements.append(Spacer(1, 2*mm))

    # Summary
    summary = resume_json.get('summary', '')
    if summary:
        elements.append(Paragraph('PROFESSIONAL SUMMARY', section_style))
        elements.append(Paragraph(str(summary), body_style))

    # Experience
    experiences = resume_json.get('experiences', [])
    if experiences:
        elements.append(Paragraph('EXPERIENCE', section_style))
        for exp in experiences:
            if isinstance(exp, dict):
                title = exp.get('title', '')
                company = exp.get('company', '')
                elements.append(Paragraph(
                    f"<b>{title}</b> — {company}", job_title_style
                ))
                for bullet in exp.get('bullets', []):
                    elements.append(Paragraph(
                        f"• {bullet}", bullet_style
                    ))

    # Education
    education = resume_json.get('education', [])
    if education:
        elements.append(Paragraph('EDUCATION', section_style))
        for edu in education:
            if isinstance(edu, dict):
                degree = edu.get('degree', '')
                institution = edu.get('institution', '')
                elements.append(Paragraph(
                    f"<b>{degree}</b> — {institution}", body_style
                ))

    # Skills
    skills = resume_json.get('skills', [])
    if skills:
        elements.append(Paragraph('SKILLS', section_style))
        for sg in skills:
            if isinstance(sg, dict):
                cat = sg.get('category') or 'Skills'
                items = sg.get('skills', [])
                if items:
                    elements.append(Paragraph(
                        f"<b>{cat}:</b> {', '.join(str(s) for s in items)}", body_style
                    ))
            elif isinstance(sg, str):
                elements.append(Paragraph(f"• {sg}", bullet_style))

    # Keywords
    keywords = resume_json.get('keywords_used', [])
    if keywords:
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(
            f"<i>Keywords: {', '.join(str(k) for k in keywords)}</i>",
            contact_style
        ))

    doc.build(elements)
    return buf.getvalue()