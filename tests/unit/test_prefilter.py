"""Unit tests for the deterministic pre-filter — no DB, no network."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from jobhunter.application.services.prefilter import PreFilter, cosine_similarity
from jobhunter.domain.enums import RemotePolicy


def _make_job(**overrides: object) -> MagicMock:
    job = MagicMock()
    job.salary_max = overrides.get("salary_max")
    job.salary_min = overrides.get("salary_min")
    job.remote_policy = overrides.get("remote_policy")
    job.company_name = overrides.get("company_name", "TestCo")
    return job


def _make_profile(**overrides: object) -> MagicMock:
    profile = MagicMock()
    profile.salary_min = overrides.get("salary_min")
    profile.salary_max = overrides.get("salary_max")
    profile.remote_preference = overrides.get("remote_preference")
    profile.visa_status = overrides.get("visa_status")
    return profile


def _make_company(**overrides: object) -> MagicMock:
    company = MagicMock()
    company.is_blacklisted = overrides.get("is_blacklisted", False)
    company.name = overrides.get("name", "TestCo")
    return company


class TestSalaryFilter:
    def test_salary_floor_fail(self) -> None:
        pf = PreFilter()
        job = _make_job(salary_max=50000.0)
        profile = _make_profile(salary_min=80000.0)
        passed, reasons = pf.check(job, profile, None)
        assert not passed
        assert any("FAIL" in r and "salary" in r.lower() for r in reasons)

    def test_salary_floor_pass(self) -> None:
        pf = PreFilter()
        job = _make_job(salary_max=100000.0)
        profile = _make_profile(salary_min=80000.0)
        passed, reasons = pf.check(job, profile, None)
        assert passed
        assert any("PASS" in r and "salary" in r.lower() for r in reasons)

    def test_salary_data_missing_passes(self) -> None:
        pf = PreFilter()
        job = _make_job(salary_max=None)
        profile = _make_profile(salary_min=80000.0)
        passed, reasons = pf.check(job, profile, None)
        assert passed
        assert any("incomplete" in r.lower() for r in reasons)


class TestRemoteFilter:
    def test_remote_required_onsite_job_fails(self) -> None:
        pf = PreFilter()
        job = _make_job(remote_policy=RemotePolicy.ONSITE.value)
        profile = _make_profile(remote_preference=RemotePolicy.REMOTE)
        passed, reasons = pf.check(job, profile, None)
        assert not passed
        assert any("FAIL" in r and "onsite" in r.lower() for r in reasons)

    def test_remote_required_remote_job_passes(self) -> None:
        pf = PreFilter()
        job = _make_job(remote_policy=RemotePolicy.REMOTE.value)
        profile = _make_profile(remote_preference=RemotePolicy.REMOTE)
        passed, reasons = pf.check(job, profile, None)
        assert passed

    def test_remote_required_hybrid_job_passes(self) -> None:
        pf = PreFilter()
        job = _make_job(remote_policy=RemotePolicy.HYBRID.value)
        profile = _make_profile(remote_preference=RemotePolicy.REMOTE)
        passed, reasons = pf.check(job, profile, None)
        assert passed


class TestBlacklist:
    def test_blacklisted_company_hard_fail(self) -> None:
        pf = PreFilter()
        job = _make_job()
        profile = _make_profile()
        company = _make_company(is_blacklisted=True, name="BadCorp")
        passed, reasons = pf.check(job, profile, company)
        assert not passed
        assert any("blacklisted" in r.lower() for r in reasons)

    def test_not_blacklisted_passes(self) -> None:
        pf = PreFilter()
        job = _make_job()
        profile = _make_profile()
        company = _make_company(is_blacklisted=False)
        passed, reasons = pf.check(job, profile, company)
        assert passed


class TestVisa:
    def test_visa_unknown_passes_with_reason(self) -> None:
        pf = PreFilter()
        job = _make_job()
        profile = _make_profile(visa_status="Needs sponsorship")
        passed, reasons = pf.check(job, profile, None)
        assert passed
        assert any("visa" in r.lower() and "unknown" in r.lower() for r in reasons)


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(a, b)) < 1e-9

    def test_known_result(self) -> None:
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        import math

        dot = 1 * 4 + 2 * 5 + 3 * 6  # 32
        norm_a = math.sqrt(1 + 4 + 9)  # sqrt(14)
        norm_b = math.sqrt(16 + 25 + 36)  # sqrt(77)
        expected = dot / (norm_a * norm_b)
        assert abs(cosine_similarity(a, b) - expected) < 1e-9

    def test_zero_vector(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="dimensions differ"):
            cosine_similarity([1.0], [1.0, 2.0])
