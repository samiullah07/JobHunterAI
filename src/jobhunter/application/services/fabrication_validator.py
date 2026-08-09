"""Fabrication validator — structural integrity check for tailored résumés.

Verifies that every concrete claim in a TailoredResume traces back to the
verified profile data. This is the STRUCTURAL enforcement of the non-fabrication
rule — it cannot be bypassed by prompt engineering.

Tolerance rules:
- Company name matching: case-insensitive, stripped whitespace.
- Title matching: case-insensitive, stripped whitespace.
- Date matching: exact match (no extending tenure).
- Skills: case-insensitive match against all profile skills.
- Technologies in bullets: each named technology must exist somewhere in the
  profile (skills list, work_experience.technologies, project.technologies).
  This catches invented tech claims.
- Rephrasing tolerance: bullets MAY rephrase achievements using different words.
  We do NOT check bullet text verbatim — only that named technologies/tools are
  present in the profile. This avoids false positives on legitimate rewording.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from jobhunter.domain.cover_letter import CoverLetter
from jobhunter.domain.resume import FabricationReport, TailoredResume

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import UserProfile


def _normalize(s: str) -> str:
    return s.strip().lower()


def _collect_profile_technologies(profile: UserProfile) -> set[str]:
    """Gather all technologies/skills from the entire profile into a normalized set."""
    techs: set[str] = set()

    if profile.skills:
        for skill in profile.skills:
            techs.add(_normalize(skill.name))

    if profile.work_experiences:
        for exp in profile.work_experiences:
            if exp.technologies:
                for t in exp.technologies:
                    techs.add(_normalize(t))

    if profile.projects:
        for proj in profile.projects:
            if proj.technologies:
                for t in proj.technologies:
                    techs.add(_normalize(t))

    return techs


def _extract_tech_terms_from_bullet(bullet: str) -> list[str]:
    """Extract candidate technology/tool tokens from a bullet point.

    Returns all tokens of length >= 2 that are not common English words.
    The caller applies _is_tech_shaped() to decide which extracted terms
    warrant a fabrication check against the profile.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]*[A-Za-z0-9+#]|[A-Za-z]+", bullet)
    terms: list[str] = []
    for token in tokens:
        if len(token) >= 2 and not _is_common_word(token):
            terms.append(token)
    return terms


def _is_tech_shaped(term: str) -> bool:
    """Conservative heuristic: does this term look like a tech/tool proper noun?

    Flagging rule — a term is considered tech-shaped if ANY of:
    1. Contains tech-special characters: +, # (e.g. C++, C#)
    2. Contains a mid-word dot with surrounding alpha (Node.js, Vue.js)
    3. Has internal uppercase after position 0 (PostgreSQL, FastAPI, TypeScript)
    4. Starts with an uppercase letter (Kubernetes, Terraform, Redis)

    Lowercase-only terms (cross-team, delivery, throughput) are NEVER
    tech-shaped and will never be flagged — they are generic prose.
    First-word-of-sentence capitalization is handled by the comprehensive
    _COMMON_WORDS set which includes resume action verbs.
    """
    if any(c in term for c in "+#"):
        return True
    if "." in term and len(term) > 3:
        return True
    if any(c.isupper() for c in term[1:]):
        return True
    return term[0].isupper()


_COMMON_WORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "with",
        "from",
        "into",
        "that",
        "this",
        "which",
        "were",
        "was",
        "are",
        "have",
        "has",
        "had",
        "been",
        "being",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "did",
        "does",
        "done",
        "not",
        "but",
        "also",
        "more",
        "most",
        "some",
        "any",
        "all",
        "each",
        "every",
        "both",
        "few",
        "many",
        "much",
        "very",
        "just",
        "about",
        "over",
        "under",
        "between",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "such",
        "own",
        "same",
        "too",
        "only",
        "then",
        "than",
        "when",
        "where",
        "how",
        "what",
        "who",
        "whom",
        "why",
        "which",
        "while",
        "until",
        "since",
        "because",
        "although",
        "though",
        "even",
        "still",
        "already",
        "yet",
        "again",
        "once",
        "here",
        "there",
        "their",
        "them",
        "they",
        "those",
        "these",
        "its",
        "our",
        "your",
        "his",
        "her",
        "its",
        "out",
        "off",
        "let",
        "got",
        "get",
        "set",
        "put",
        "use",
        "used",
        "using",
        "make",
        "made",
        "built",
        "build",
        "run",
        "ran",
        "led",
        "lead",
        "helped",
        "create",
        "created",
        "developed",
        "implemented",
        "designed",
        "managed",
        "improved",
        "increased",
        "reduced",
        "delivered",
        "maintained",
        "optimized",
        "launched",
        "deployed",
        "integrated",
        "streamlined",
        "collaborated",
        "achieved",
        "ensured",
        "established",
        "facilitated",
        "leveraged",
        "spearheaded",
        "orchestrated",
        "architected",
        "drove",
        "driving",
        "resulting",
        "results",
        "across",
        "team",
        "teams",
        "company",
        "companies",
        "project",
        "projects",
        "system",
        "systems",
        "solution",
        "solutions",
        "service",
        "services",
        "application",
        "applications",
        "platform",
        "data",
        "based",
        "level",
        "high",
        "new",
        "key",
        "top",
        "best",
        "full",
        "time",
        "year",
        "years",
        "month",
        "months",
        "day",
        "days",
        "work",
        "working",
        "worked",
        # Generic industry terms/abbreviations (not specific technologies)
        "api",
        "apis",
        "saas",
        "paas",
        "iaas",
        "kpi",
        "kpis",
        "sla",
        "slas",
        "roi",
        "sdk",
        "sdks",
        "cli",
        "gui",
        "ide",
        "iot",
        "mvp",
        "poc",
        "cicd",
        "devops",
        "agile",
        "scrum",
        "kanban",
        "qa",
        "uat",
        "crud",
        "rest",
        "restful",
        "http",
        "https",
        "ssh",
        "ssl",
        "tls",
        "sql",
        "nosql",
        "orm",
        "etl",
        "elt",
        "ml",
        "ai",
        "llm",
        "nlp",
        "oop",
        "solid",
        "dry",
        "kiss",
        "yagni",
        "tdd",
        "bdd",
        "frontend",
        "backend",
        "fullstack",
        "microservices",
        "monolith",
        "ci",
        "cd",
        "ops",
        "sre",
        "cto",
        "ceo",
        "vp",
        "eng",
        # Common cover-letter/business words that appear capitalized
        "dear",
        "sincerely",
        "regards",
        "thank",
        "thanks",
        "hiring",
        "manager",
        "position",
        "role",
        "opportunity",
        "experience",
        "contribute",
        "forward",
        "looking",
        "hearing",
        "discussing",
        "interest",
        "interested",
        "apply",
        "applying",
        "writing",
        "consider",
        "considering",
        "consideration",
        "pleased",
        "excited",
        "eager",
        "thrilled",
        "passionate",
        "mission",
        "vision",
        "growth",
        "impact",
        "industry",
        "professional",
        "candidate",
        "background",
        "expertise",
        "skills",
        "knowledge",
        "abilities",
        "qualifications",
        "requirements",
        "responsibilities",
        "environment",
        "culture",
        "engineering",
        "development",
        "technology",
        "technologies",
        "technical",
        "software",
        "scalable",
        "production",
        "performance",
        "quality",
        "innovation",
        "innovative",
    ]
)


def _is_common_word(word: str) -> bool:
    return word.lower() in _COMMON_WORDS


def validate(tailored: TailoredResume, profile: UserProfile) -> FabricationReport:
    """Validate that every claim in the tailored résumé traces to the profile."""
    violations: list[str] = []

    all_techs = _collect_profile_technologies(profile)

    # Validate experiences
    profile_experiences = profile.work_experiences or []
    for exp in tailored.experiences:
        matched = False
        for pexp in profile_experiences:
            if _normalize(exp.company) == _normalize(pexp.company_name) and _normalize(
                exp.title
            ) == _normalize(pexp.title):
                matched = True
                # Check dates are not extended
                if exp.start_date != pexp.start_date:
                    violations.append(
                        f"Experience '{exp.title} @ {exp.company}': "
                        f"start_date {exp.start_date} != profile {pexp.start_date}"
                    )
                if pexp.end_date is not None and exp.end_date != pexp.end_date:
                    violations.append(
                        f"Experience '{exp.title} @ {exp.company}': "
                        f"end_date {exp.end_date} != profile {pexp.end_date}"
                    )
                # Bullet tech check: flag invented proper-noun technologies.
                # Rule: a term is a violation when it is (a) tech-shaped
                # (capitalized / contains +#/.), (b) length >= 3, (c) not a
                # common word, AND (d) absent from the full profile tech set.
                # Lowercase prose and action verbs pass through untouched.
                for bullet in exp.bullets:
                    for tech in _extract_tech_terms_from_bullet(bullet):
                        if (
                            len(tech) >= 3
                            and not _is_common_word(tech)
                            and _is_tech_shaped(tech)
                            and _normalize(tech) not in all_techs
                        ):
                            violations.append(
                                f"Bullet in '{exp.title} @ {exp.company}' "
                                f"references technology '{tech}' "
                                f"not found in verified profile"
                            )
                break
        if not matched:
            violations.append(
                f"Experience '{exp.title} @ {exp.company}' has no matching profile entry"
            )

    # Validate education
    profile_educations = profile.educations or []
    for edu in tailored.education:
        matched = False
        for pedu in profile_educations:
            if _normalize(edu.institution) == _normalize(pedu.institution) and _normalize(
                edu.degree
            ) == _normalize(pedu.degree):
                matched = True
                break
        if not matched:
            violations.append(
                f"Education '{edu.degree} @ {edu.institution}' has no matching profile entry"
            )

    # Validate skills — every skill in tailored must be in profile
    profile_skill_names = {_normalize(s.name) for s in (profile.skills or [])}
    # Also include technologies from experiences and projects
    all_skill_sources = profile_skill_names | all_techs
    for group in tailored.skills:
        for skill in group.skills:
            if _normalize(skill) not in all_skill_sources:
                violations.append(f"Skill '{skill}' not in verified profile")

    # Validate certifications
    profile_certs = {_normalize(c.name) for c in (profile.certifications or [])}
    for cert in tailored.certifications:
        if _normalize(cert) not in profile_certs:
            violations.append(f"Certification '{cert}' not in verified profile")

    # Validate projects
    profile_projects = {_normalize(p.name) for p in (profile.projects or [])}
    for proj in tailored.projects:
        if _normalize(proj.name) not in profile_projects:
            violations.append(f"Project '{proj.name}' has no matching profile entry")

    return FabricationReport(is_clean=len(violations) == 0, violations=violations)


def _collect_profile_employers(profile: UserProfile) -> set[str]:
    """Normalized set of company names the candidate actually worked at."""
    employers: set[str] = set()
    if profile.work_experiences:
        for exp in profile.work_experiences:
            employers.add(_normalize(exp.company_name))
    return employers


def _collect_profile_certs(profile: UserProfile) -> set[str]:
    return {_normalize(c.name) for c in (profile.certifications or [])}


def _collect_profile_degrees(profile: UserProfile) -> set[str]:
    degrees: set[str] = set()
    if profile.educations:
        for edu in profile.educations:
            degrees.add(_normalize(edu.degree))
            if edu.institution:
                degrees.add(_normalize(edu.institution))
    return degrees


def _build_allowed_tokens(letter: CoverLetter, profile: UserProfile) -> set[str]:
    """Build a set of tokens that are allowed in cover letter prose.

    These are NOT technologies — they are contextual tokens from the job,
    the candidate's profile, and common letter language that would otherwise
    trigger the tech-shaped heuristic due to capitalization.
    """
    allowed: set[str] = set()

    # Target company and role tokens are expected in the letter
    for word in letter.company_name.split():
        allowed.add(_normalize(word))
    for word in letter.role.split():
        allowed.add(_normalize(word))

    # Profile employer name tokens (e.g. "Acme", "Corp")
    if profile.work_experiences:
        for exp in profile.work_experiences:
            for word in exp.company_name.split():
                allowed.add(_normalize(word))
            for word in exp.title.split():
                allowed.add(_normalize(word))

    # Education institution/degree tokens
    if profile.educations:
        for edu in profile.educations:
            for word in edu.institution.split():
                allowed.add(_normalize(word))
            for word in edu.degree.split():
                allowed.add(_normalize(word))

    # Certification name tokens
    if profile.certifications:
        for cert in profile.certifications:
            for word in cert.name.split():
                allowed.add(_normalize(word))

    return allowed


def validate_cover_letter(letter: CoverLetter, profile: UserProfile) -> FabricationReport:
    """Validate cover letter prose against verified profile.

    Tolerance rules for cover letters:
    - The TARGET company (letter.company_name) and role (letter.role) are
      expected to appear in the prose and MUST NOT be flagged.
    - Tokens from profile employers, titles, institutions, degrees, and
      certs are allowed (they are context, not invented tech).
    - Aspirational/motivational framing is allowed ("excited to bring",
      "drawn to your mission") — only FACTUAL CLAIMS are checked.
    - Named technologies/tools not in profile → violation.
    - Claims of having WORKED at an employer not in the profile's work
      history → violation. (Target company is excluded from this check.)
    - Degrees/certifications/institutions not in profile → violation.
    """
    violations: list[str] = []

    all_techs = _collect_profile_technologies(profile)
    profile_employers = _collect_profile_employers(profile)
    profile_certs = _collect_profile_certs(profile)
    profile_degrees = _collect_profile_degrees(profile)
    allowed_tokens = _build_allowed_tokens(letter, profile)

    # The target company is legitimate — exclude from employer fabrication check
    target_company_norm = _normalize(letter.company_name)

    # All prose fields to scan
    prose_fields = [letter.opening, *letter.body_paragraphs, letter.closing]

    for paragraph in prose_fields:
        for term in _extract_tech_terms_from_bullet(paragraph):
            if (
                len(term) >= 3
                and not _is_common_word(term)
                and _is_tech_shaped(term)
                and _normalize(term) not in all_techs
                and _normalize(term) not in allowed_tokens
            ):
                violations.append(
                    f"Cover letter references technology '{term}' not found in verified profile"
                )

    # Check for employer claims: look for "at X" / "with X" patterns
    # that reference companies NOT in the profile (excluding target)
    _check_employer_claims(prose_fields, profile_employers, target_company_norm, violations)

    # Check certifications/degrees mentioned in prose
    _check_credential_claims(prose_fields, profile_certs, profile_degrees, violations)

    return FabricationReport(is_clean=len(violations) == 0, violations=violations)


def _check_employer_claims(
    paragraphs: list[str],
    profile_employers: set[str],
    target_company_norm: str,
    violations: list[str],
) -> None:
    """Flag claims of having worked at companies not in the profile.

    Pattern: looks for capitalized multi-word sequences that appear after
    work-indicator phrases like "at", "with", "for", "worked at".
    Only flags terms that are tech-shaped (capitalized) and NOT in
    the known employer set or the target company.
    """
    work_phrases = re.compile(
        r"(?:worked?\s+(?:at|for|with)|employed\s+(?:at|by)|"
        r"(?:my\s+time|experience)\s+(?:at|with))\s+([A-Z][A-Za-z0-9 &.'-]+)",
        re.IGNORECASE,
    )
    for paragraph in paragraphs:
        for match in work_phrases.finditer(paragraph):
            company = match.group(1).strip().rstrip(".,;:")
            norm = _normalize(company)
            if norm != target_company_norm and norm not in profile_employers and len(company) >= 3:
                violations.append(
                    f"Cover letter claims work at '{company}' "
                    f"not found in verified profile employers"
                )


def _check_credential_claims(
    paragraphs: list[str],
    profile_certs: set[str],
    profile_degrees: set[str],
    violations: list[str],
) -> None:
    """Flag degrees/certifications mentioned in prose that aren't in profile."""
    cert_patterns = re.compile(
        r"(?:certified|certification|certificate)\s+(?:in\s+)?([A-Z][A-Za-z0-9 +#.-]+)",
        re.IGNORECASE,
    )
    degree_patterns = re.compile(
        r"(?:(?:B\.?S\.?|M\.?S\.?|Ph\.?D\.?|MBA|Bachelor|Master|Doctor)\s+"
        r"(?:of\s+|in\s+)?[A-Z][A-Za-z ]+)",
        re.IGNORECASE,
    )
    for paragraph in paragraphs:
        for match in cert_patterns.finditer(paragraph):
            cert = match.group(1).strip().rstrip(".,;:")
            if _normalize(cert) not in profile_certs and len(cert) >= 3:
                violations.append(
                    f"Cover letter references certification '{cert}' not found in verified profile"
                )
        for match in degree_patterns.finditer(paragraph):
            degree = match.group(0).strip().rstrip(".,;:")
            if (
                _normalize(degree) not in profile_degrees
                and not any(_normalize(degree) in d for d in profile_degrees)
                and not any(d in _normalize(degree) for d in profile_degrees)
            ):
                violations.append(
                    f"Cover letter references degree '{degree}' not found in verified profile"
                )
