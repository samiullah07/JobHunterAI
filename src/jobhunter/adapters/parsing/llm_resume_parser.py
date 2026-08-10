"""LLM-backed résumé parser — implements the ResumeParser port.

Extracts text via the text_extractor, then calls an LLM (via the LlmClient port)
to structure the raw text into a ParsedResume proposal.
"""

from __future__ import annotations

import json

from jobhunter.adapters.parsing.text_extractor import extract_text
from jobhunter.application.ports.llm import LlmClient
from jobhunter.domain.profile import ParsedResume

_SYSTEM_PROMPT = """\
You are a résumé parser. Given raw text extracted from a résumé document, \
produce a structured JSON object matching the provided schema. \
Extract ONLY what is explicitly stated — do not infer, fabricate, or embellish. \
For fields you cannot determine, use null. \
Include a "confidence" map with float values 0.0–1.0 for each field you populate."""

_SCHEMA_HINT = json.dumps(ParsedResume.model_json_schema(), indent=2)




def _normalize_parsed_fields(raw: dict) -> dict:
    """Map common LLM output field names to ParsedResume expected names."""
    d = dict(raw)

    # Name
    if "full_name" not in d and "name" in d:
        d["full_name"] = d.pop("name")

    # Contact info (may be nested)
    contact = d.pop("contact", {}) or {}
    if isinstance(contact, dict):
        if "email" not in d and "email" in contact:
            d["email"] = contact["email"]
        if "phone" not in d and "phone" in contact:
            d["phone"] = contact["phone"]
        if "location" not in d and "location" in contact:
            d["location"] = contact["location"]

    # Profiles/links (may be nested)
    profiles = d.pop("profiles", {}) or {}
    if isinstance(profiles, dict):
        for key in ("github", "github_url", "githubUrl"):
            if key in profiles and "github_url" not in d:
                d["github_url"] = profiles[key]
        for key in ("linkedin", "linkedin_url", "linkedinUrl"):
            if key in profiles and "linkedin_url" not in d:
                d["linkedin_url"] = profiles[key]
        for key in ("website", "website_url", "websiteUrl"):
            if key in profiles and "website_url" not in d:
                d["website_url"] = profiles[key]
        for key in ("portfolio", "portfolio_url", "portfolioUrl"):
            if key in profiles and "portfolio_url" not in d:
                d["portfolio_url"] = profiles[key]

    # Skills (aggressive fuzzy match — catches any key containing 'skill')
    if "skills" not in d:
        for key in list(d.keys()):
            if "skill" in key.lower():
                d["skills"] = d.pop(key)
                break

    # Work experiences (aggressive fuzzy match)
    if "work_experiences" not in d:
        for key in list(d.keys()):
            if any(w in key.lower() for w in ("experience", "employment", "work_hist", "career")):
                d["work_experiences"] = d.pop(key)
                break

    # Educations (aggressive fuzzy match)
    if "educations" not in d:
        for key in list(d.keys()):
            if "educ" in key.lower():
                d["educations"] = d.pop(key)
                break

    # Projects (aggressive fuzzy match)
    if "projects" not in d:
        for key in list(d.keys()):
            if "project" in key.lower():
                d["projects"] = d.pop(key)
                break

    # Summary (aggressive fuzzy match)
    if "summary" not in d:
        for key in list(d.keys()):
            if "summary" in key.lower() or "profile" in key.lower() or "objective" in key.lower():
                d["summary"] = d.pop(key)
                break
    # Flatten skills if they are grouped by category
    if "skills" in d and isinstance(d["skills"], dict):
        flat = []
        for cat, items in d["skills"].items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str):
                        flat.append({"name": item, "category": cat})
                    elif isinstance(item, dict):
                        item.setdefault("category", cat)
                        flat.append(item)
            elif isinstance(items, str):
                flat.append({"name": items, "category": cat})
        d["skills"] = flat
    elif "skills" in d and isinstance(d["skills"], list):
        normalized = []
        for s in d["skills"]:
            if isinstance(s, str):
                normalized.append({"name": s})
            elif isinstance(s, dict):
                normalized.append(s)
        d["skills"] = normalized

    # Work experiences
    if "work_experiences" not in d:
        for key in ("workExperience", "work_experience", "experience", "experiences", "employment"):
            if key in d:
                d["work_experiences"] = d.pop(key)
                break
    if "work_experiences" in d and isinstance(d["work_experiences"], list):
        for exp in d["work_experiences"]:
            if isinstance(exp, dict):
                if "company" in exp and "company_name" not in exp:
                    exp["company_name"] = exp.pop("company")
                if "is_current" not in exp:
                    exp["is_current"] = False

    # Educations
    if "educations" not in d:
        for key in ("education", "Education"):
            if key in d:
                d["educations"] = d.pop(key)
                break
    # Wrap single education dict in a list
    if "educations" in d and isinstance(d["educations"], dict):
        d["educations"] = [d["educations"]]
    if "educations" in d and isinstance(d["educations"], list):
        for edu in d["educations"]:
            if isinstance(edu, dict):
                if "school" in edu and "institution" not in edu:
                    edu["institution"] = edu.pop("school")
                if "university" in edu and "institution" not in edu:
                    edu["institution"] = edu.pop("university")
                if "institution" not in edu:
                    edu["institution"] = "Unknown"
                if "start_date" not in edu:
                    edu["start_date"] = "2020-01-01"
                if "field" in edu and "field_of_study" not in edu:
                    edu["field_of_study"] = edu.pop("field")

    # Projects
    if "projects" not in d and "Projects" in d:
        d["projects"] = d.pop("Projects")

    # Certifications
    if "certifications" not in d:
        for key in ("Certifications", "certs", "certificates"):
            if key in d:
                d["certifications"] = d.pop(key)
                break

    # Summary variations
    if "summary" not in d:
        for key in ("professionalSummary", "professional_summary", "profileSummary"):
            if key in d:
                d["summary"] = d.pop(key)
                break

    # Projects variations
    if "projects" not in d:
        for key in ("selectedProjects", "selected_projects", "Projects"):
            if key in d:
                d["projects"] = d.pop(key)
                break

    # Confidence variations
    if "confidence" not in d:
        for key in ("confidenceMap", "confidence_map"):
            if key in d:
                d["confidence"] = d.pop(key)
                break

    return d

class LlmResumeParser:
    """Implements ResumeParser: text extraction + LLM structuring."""

    def __init__(self, llm: LlmClient) -> None:
        self._llm = llm

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedResume:
        raw_text = extract_text(file_bytes, filename)
        user_prompt = f"Parse the following résumé text:\n\n{raw_text}"
        result = await self._llm.complete_json(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            schema_hint=_SCHEMA_HINT,
        )
        result["source_filename"] = filename
        import logging
        logging.warning(f"RAW LLM KEYS: {list(result.keys())}")
        logging.warning(f"RAW SKILLS KEY CHECK: technicalSkills={result.get('technicalSkills','MISS')} skills={result.get('skills','MISS')} technical_skills={result.get('technical_skills','MISS')}")
        # Normalize Groq's preferred field names to ParsedResume schema
        result = _normalize_parsed_fields(result)
        return ParsedResume.model_validate(result)
