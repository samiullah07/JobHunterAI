"""Unit tests for resume rendering — offline, no Playwright (PDF tested in integration)."""

from __future__ import annotations

import json
from datetime import date

from jobhunter.adapters.rendering.resume_renderer import (
    to_docx,
    to_html,
    to_json,
    to_markdown,
)
from jobhunter.domain.resume import (
    TailoredEducation,
    TailoredExperience,
    TailoredProject,
    TailoredResume,
    TailoredSkillGroup,
)


def _sample_resume() -> TailoredResume:
    return TailoredResume(
        full_name="Alice Johnson",
        email="alice@example.com",
        phone="555-0123",
        location="San Francisco, CA",
        linkedin_url="https://linkedin.com/in/alice",
        github_url="https://github.com/alice",
        summary="Experienced backend engineer specializing in Python.",
        experiences=[
            TailoredExperience(
                company="WidgetCo",
                title="Staff Engineer",
                start_date=date(2021, 3, 1),
                is_current=True,
                bullets=[
                    "Led migration of monolith to microservices",
                    "Reduced p99 latency by 40%",
                ],
            ),
        ],
        education=[
            TailoredEducation(
                institution="Stanford University",
                degree="M.S.",
                field_of_study="Computer Science",
                start_date=date(2017, 9, 1),
                end_date=date(2019, 6, 1),
            ),
        ],
        skills=[
            TailoredSkillGroup(category="Languages", skills=["Python", "Go"]),
        ],
        projects=[
            TailoredProject(
                name="FastCache",
                description="In-memory cache with TTL eviction",
                technologies=["Python", "Redis"],
            ),
        ],
        certifications=["AWS Solutions Architect"],
    )


class TestToJson:
    def test_valid_json(self) -> None:
        result = to_json(_sample_resume())
        parsed = json.loads(result)
        assert parsed["full_name"] == "Alice Johnson"
        assert parsed["email"] == "alice@example.com"

    def test_experiences_serialized(self) -> None:
        result = to_json(_sample_resume())
        parsed = json.loads(result)
        assert len(parsed["experiences"]) == 1
        assert parsed["experiences"][0]["company"] == "WidgetCo"


class TestToMarkdown:
    def test_contains_name_heading(self) -> None:
        md = to_markdown(_sample_resume())
        assert "# Alice Johnson" in md

    def test_contains_contact_info(self) -> None:
        md = to_markdown(_sample_resume())
        assert "alice@example.com" in md
        assert "555-0123" in md
        assert "San Francisco, CA" in md

    def test_contains_sections(self) -> None:
        md = to_markdown(_sample_resume())
        assert "## Summary" in md
        assert "## Experience" in md
        assert "## Education" in md
        assert "## Skills" in md
        assert "## Projects" in md
        assert "## Certifications" in md

    def test_experience_bullets(self) -> None:
        md = to_markdown(_sample_resume())
        assert "- Led migration of monolith to microservices" in md
        assert "- Reduced p99 latency by 40%" in md

    def test_empty_resume_renders(self) -> None:
        minimal = TailoredResume(full_name="Bob", email="bob@test.com")
        md = to_markdown(minimal)
        assert "# Bob" in md
        assert "bob@test.com" in md


class TestToDocx:
    def test_produces_bytes(self) -> None:
        data = to_docx(_sample_resume())
        assert isinstance(data, bytes)
        assert len(data) > 100

    def test_valid_docx_header(self) -> None:
        data = to_docx(_sample_resume())
        assert data[:2] == b"PK"

    def test_no_tables_in_docx(self) -> None:
        from io import BytesIO

        from docx import Document

        data = to_docx(_sample_resume())
        doc = Document(BytesIO(data))
        assert len(doc.tables) == 0


class TestToHtml:
    def test_valid_html_structure(self) -> None:
        html = to_html(_sample_resume())
        assert "<!DOCTYPE html>" in html
        assert "<h1>" in html
        assert "</body></html>" in html

    def test_name_in_h1(self) -> None:
        html = to_html(_sample_resume())
        assert "<h1>Alice Johnson</h1>" in html

    def test_escapes_special_chars(self) -> None:
        resume = TailoredResume(
            full_name="O'Brien & Sons",
            email="test@test.com",
            summary="Work with <script> and & symbols",
        )
        html = to_html(resume)
        assert "&lt;script&gt;" in html
        assert "&amp;" in html
