"""API tests for /profiles endpoints — uses httpx AsyncClient with dep overrides."""

import io
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from docx import Document
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.adapters.parsing.llm_resume_parser import LlmResumeParser
from jobhunter.api.profiles import _get_parser
from jobhunter.infrastructure.db.session import get_session
from jobhunter.main import app
from tests.fakes.llm import FakeStructuringLLM

pytestmark = pytest.mark.integration


def _fake_parser() -> LlmResumeParser:
    return LlmResumeParser(llm=FakeStructuringLLM())


@pytest.fixture(autouse=True)
def _override_session(async_session: AsyncSession) -> Generator[None, Any]:
    async def _override() -> AsyncGenerator[AsyncSession]:
        yield async_session

    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def _override_parser() -> Generator[None, Any]:
    app.dependency_overrides[_get_parser] = _fake_parser
    yield
    app.dependency_overrides.pop(_get_parser, None)


def _make_docx(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestProfileCRUD:
    async def test_create_and_get_profile(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "full_name": "Test User",
                "email": "test@example.com",
                "headline": "Developer",
                "skills": [{"name": "Python", "category": "Language"}],
            }
            resp = await client.post("/profiles", json=payload)
            assert resp.status_code == 201
            data = resp.json()
            profile_id = data["id"]
            assert uuid.UUID(profile_id)

            resp2 = await client.get(f"/profiles/{profile_id}")
            assert resp2.status_code == 200
            body = resp2.json()
            assert body["full_name"] == "Test User"
            assert body["email"] == "test@example.com"
            assert len(body["skills"]) == 1

    async def test_get_nonexistent_returns_404(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fake_id = str(uuid.uuid4())
            resp = await client.get(f"/profiles/{fake_id}")
            assert resp.status_code == 404


class TestIngestResume:
    @pytest.mark.usefixtures("_override_parser")
    async def test_ingest_returns_proposal(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            docx_bytes = _make_docx("Jane Doe\nSenior Engineer")
            resp = await client.post(
                "/profiles/ingest-resume",
                files={"file": ("resume.docx", docx_bytes, "application/octet-stream")},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["source_filename"] == "resume.docx"
            assert body["full_name"] == "Jane Doe"
            assert "confidence" in body
