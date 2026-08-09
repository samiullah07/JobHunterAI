"""Unit tests for the LLM-backed résumé parser with a fake LLM — no network."""

import io

import pytest
from docx import Document

from jobhunter.adapters.parsing.llm_resume_parser import LlmResumeParser
from tests.fakes.llm import FakeStructuringLLM


def _make_docx(text: str) -> bytes:
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestLlmResumeParser:
    @pytest.fixture
    def parser(self) -> LlmResumeParser:
        return LlmResumeParser(llm=FakeStructuringLLM())

    async def test_parse_returns_parsed_resume(self, parser: LlmResumeParser) -> None:
        docx_bytes = _make_docx("Jane Doe\nSenior Engineer\njane@example.com")
        result = await parser.parse(docx_bytes, "resume.docx")
        assert result.source_filename == "resume.docx"
        assert result.full_name == "Jane Doe"
        assert result.email == "jane@example.com"
        assert result.confidence["full_name"] == 0.99

    async def test_parse_includes_skills(self, parser: LlmResumeParser) -> None:
        docx_bytes = _make_docx("Some resume text")
        result = await parser.parse(docx_bytes, "cv.docx")
        assert result.skills is not None
        assert len(result.skills) == 2
        assert result.skills[0].name == "Python"

    async def test_parse_includes_work_experience(self, parser: LlmResumeParser) -> None:
        docx_bytes = _make_docx("Some resume text")
        result = await parser.parse(docx_bytes, "cv.docx")
        assert result.work_experiences is not None
        assert len(result.work_experiences) == 1
        assert result.work_experiences[0].company_name == "Acme Corp"
        assert result.work_experiences[0].is_current is True

    async def test_custom_response(self) -> None:
        custom = FakeStructuringLLM(
            response={
                "full_name": "Custom Name",
                "email": "custom@test.com",
                "confidence": {"full_name": 1.0},
            }
        )
        parser = LlmResumeParser(llm=custom)
        docx_bytes = _make_docx("anything")
        result = await parser.parse(docx_bytes, "test.docx")
        assert result.full_name == "Custom Name"
        assert result.email == "custom@test.com"
