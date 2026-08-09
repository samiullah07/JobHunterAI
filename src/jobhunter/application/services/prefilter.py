"""Deterministic pre-filter — hard constraints, no LLM, no I/O."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from jobhunter.domain.enums import RemotePolicy

if TYPE_CHECKING:
    from jobhunter.infrastructure.db.models import Company, Job, UserProfile


class PreFilter:
    """Pure-function checks that eliminate jobs before expensive LLM scoring."""

    def check(
        self, job: Job, profile: UserProfile, company: Company | None
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        failed = False

        self._check_salary(job, profile, reasons)
        self._check_remote(job, profile, reasons)
        self._check_visa(job, profile, company, reasons)
        self._check_blacklist(company, reasons)

        for r in reasons:
            if r.startswith("FAIL:"):
                failed = True
                break

        return (not failed, reasons)

    def _check_salary(self, job: Job, profile: UserProfile, reasons: list[str]) -> None:
        if profile.salary_min is None or job.salary_max is None:
            reasons.append("PASS: salary data incomplete — not filtering")
            return
        if job.salary_max < profile.salary_min:
            reasons.append(
                f"FAIL: job max salary ({job.salary_max}) "
                f"below profile minimum ({profile.salary_min})"
            )
        else:
            reasons.append("PASS: salary within acceptable range")

    def _check_remote(self, job: Job, profile: UserProfile, reasons: list[str]) -> None:
        if profile.remote_preference is None:
            reasons.append("PASS: no remote preference set")
            return
        if profile.remote_preference == RemotePolicy.REMOTE:
            if job.remote_policy in (RemotePolicy.REMOTE.value, RemotePolicy.HYBRID.value, None):
                reasons.append("PASS: remote/hybrid compatible with remote preference")
            else:
                reasons.append("FAIL: job is onsite but profile requires remote")
        else:
            reasons.append("PASS: remote policy compatible")

    def _check_visa(
        self, job: Job, profile: UserProfile, company: Company | None, reasons: list[str]
    ) -> None:
        needs_sponsorship = profile.visa_status and "sponsor" in profile.visa_status.lower()
        if not needs_sponsorship:
            reasons.append("PASS: no visa sponsorship needed")
            return
        reasons.append("PASS: visa sponsorship needed — unknown if job provides it (proceeding)")

    def _check_blacklist(self, company: Company | None, reasons: list[str]) -> None:
        if company is None:
            reasons.append("PASS: company not in system — no blacklist status")
            return
        if company.is_blacklisted:
            reasons.append(f"FAIL: company '{company.name}' is blacklisted")
        else:
            reasons.append("PASS: company not blacklisted")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        msg = f"Vector dimensions differ: {len(a)} vs {len(b)}"
        raise ValueError(msg)
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
