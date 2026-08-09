"""Domain DTOs for tailored résumé generation and ATS analysis."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class TailoredExperience(BaseModel):
    company: str
    title: str
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    bullets: list[str] = []


class TailoredEducation(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: date
    end_date: date | None = None


class TailoredProject(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str] = []


class TailoredSkillGroup(BaseModel):
    category: str | None = None
    skills: list[str]


class TailoredResume(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    summary: str | None = None
    experiences: list[TailoredExperience] = []
    education: list[TailoredEducation] = []
    projects: list[TailoredProject] = []
    skills: list[TailoredSkillGroup] = []
    certifications: list[str] = []
    keywords_used: list[str] = []


class AtsAnalysis(BaseModel):
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    score: float = 0.0
    suggestions: list[str] = []


class FabricationReport(BaseModel):
    is_clean: bool = True
    violations: list[str] = []


class ResumeGenerationResult(BaseModel):
    resume_version_id: str | None = None
    storage_keys: dict[str, str] = {}
    ats_analysis: AtsAnalysis = AtsAnalysis()
    fabrication_report: FabricationReport = FabricationReport()
    fabrication_detected: bool = False
