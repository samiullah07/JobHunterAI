"""ATS keyword analysis — deterministic, no LLM, no network."""

from __future__ import annotations

import re

from jobhunter.domain.resume import AtsAnalysis

_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "can",
        "could",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "my",
        "your",
        "our",
        "their",
        "with",
        "from",
        "by",
        "as",
        "not",
        "no",
        "nor",
        "so",
        "if",
        "then",
        "than",
        "also",
        "very",
        "just",
        "about",
        "more",
        "some",
        "any",
        "all",
        "each",
        "every",
        "both",
        "few",
        "many",
        "much",
        "such",
        "only",
        "own",
        "same",
        "too",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "up",
        "down",
        "off",
        "over",
    ]
)

_MIN_WORD_LEN = 3


def extract_keywords(text: str) -> list[str]:
    """Extract notable terms from text (deterministic, no LLM).

    Strategy: tokenize, lowercase, strip stopwords, keep terms >= 3 chars,
    deduplicate preserving first-occurrence order.
    """
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./-]*[a-zA-Z0-9+#]|[a-zA-Z]", text)
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        lower = token.lower()
        if lower in _STOPWORDS or len(lower) < _MIN_WORD_LEN:
            continue
        if lower not in seen:
            seen.add(lower)
            keywords.append(lower)
    return keywords


def analyze(resume_text: str, job_keywords: list[str]) -> AtsAnalysis:
    """Compare résumé text against job keywords to produce ATS analysis."""
    resume_lower = resume_text.lower()
    matched: list[str] = []
    missing: list[str] = []

    for kw in job_keywords:
        if kw.lower() in resume_lower:
            matched.append(kw)
        else:
            missing.append(kw)

    total = len(job_keywords)
    score = len(matched) / total if total > 0 else 0.0

    suggestions: list[str] = []
    for kw in missing[:10]:
        suggestions.append(f"Consider incorporating '{kw}' if your profile supports it")

    return AtsAnalysis(
        matched_keywords=matched,
        missing_keywords=missing,
        score=score,
        suggestions=suggestions,
    )
