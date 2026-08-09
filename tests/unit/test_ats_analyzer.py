"""Unit tests for the ATS keyword analyzer — deterministic, no network."""

from __future__ import annotations

from jobhunter.application.services.ats_analyzer import analyze, extract_keywords


class TestExtractKeywords:
    def test_removes_stopwords(self) -> None:
        keywords = extract_keywords("the quick brown fox and the lazy dog")
        assert "the" not in keywords
        assert "and" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords

    def test_deduplicates(self) -> None:
        keywords = extract_keywords("Python python PYTHON")
        assert keywords.count("python") == 1

    def test_keeps_tech_terms(self) -> None:
        keywords = extract_keywords("Experience with Python, PostgreSQL, and Docker")
        assert "python" in keywords
        assert "postgresql" in keywords
        assert "docker" in keywords

    def test_skips_short_words(self) -> None:
        keywords = extract_keywords("Go is a good language")
        assert "is" not in keywords

    def test_real_job_description(self) -> None:
        jd = (
            "We need a Senior Backend Engineer with Python, FastAPI, PostgreSQL, "
            "Docker, and Kubernetes experience. Must have strong distributed systems "
            "knowledge and experience with microservices architecture."
        )
        keywords = extract_keywords(jd)
        assert "python" in keywords
        assert "fastapi" in keywords
        assert "postgresql" in keywords
        assert "docker" in keywords
        assert "kubernetes" in keywords


class TestAnalyze:
    def test_all_matched(self) -> None:
        resume = "Experienced with Python and Docker in distributed systems"
        keywords = ["python", "docker", "distributed"]
        result = analyze(resume, keywords)
        assert result.score == 1.0
        assert result.missing_keywords == []
        assert set(result.matched_keywords) == {"python", "docker", "distributed"}

    def test_partial_match(self) -> None:
        resume = "Expert in Python development"
        keywords = ["python", "docker", "kubernetes"]
        result = analyze(resume, keywords)
        assert len(result.matched_keywords) == 1
        assert len(result.missing_keywords) == 2
        assert abs(result.score - 1 / 3) < 0.01

    def test_no_match(self) -> None:
        resume = "I am a baker"
        keywords = ["python", "docker"]
        result = analyze(resume, keywords)
        assert result.score == 0.0
        assert len(result.missing_keywords) == 2

    def test_empty_keywords(self) -> None:
        result = analyze("some resume text", [])
        assert result.score == 0.0
        assert result.matched_keywords == []

    def test_suggestions_for_missing(self) -> None:
        resume = "Python developer"
        keywords = ["python", "docker", "kubernetes"]
        result = analyze(resume, keywords)
        assert len(result.suggestions) > 0
        assert any("docker" in s for s in result.suggestions)
