"""Unit tests for scoring domain DTOs — weights, components, validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jobhunter.domain.scoring import ScoreComponents, WeightConfig


class TestScoreComponents:
    def test_clamps_above_one(self) -> None:
        sc = ScoreComponents(skills=1.5, experience=0.5)
        assert sc.skills == 1.0

    def test_clamps_below_zero(self) -> None:
        sc = ScoreComponents(skills=-0.3)
        assert sc.skills == 0.0

    def test_valid_values_pass(self) -> None:
        sc = ScoreComponents(skills=0.8, experience=0.6)
        assert sc.skills == 0.8
        assert sc.experience == 0.6

    def test_defaults_to_zero(self) -> None:
        sc = ScoreComponents()
        assert sc.skills == 0.0
        assert sc.growth == 0.0

    def test_rejects_string_non_numeric(self) -> None:
        with pytest.raises(ValidationError, match="skills"):
            ScoreComponents(skills="high")

    def test_rejects_none(self) -> None:
        with pytest.raises(ValidationError, match="skills"):
            ScoreComponents(skills=None)

    def test_rejects_list_value(self) -> None:
        with pytest.raises(ValidationError, match="experience"):
            ScoreComponents(experience=[0.5])

    def test_rejects_dict_value(self) -> None:
        with pytest.raises(ValidationError, match="salary"):
            ScoreComponents(salary={"value": 0.8})

    def test_missing_field_defaults_to_zero(self) -> None:
        """Missing field → 0.0 (model did not score this dimension)."""
        sc = ScoreComponents(skills=0.9)
        assert sc.growth == 0.0
        assert sc.visa == 0.0


class TestWeightConfig:
    def test_default_weights_sum_to_one(self) -> None:
        wc = WeightConfig()
        total = (
            wc.skills
            + wc.experience
            + wc.location
            + wc.salary
            + wc.visa
            + wc.remote
            + wc.tech_stack
            + wc.industry
            + wc.culture
            + wc.growth
        )
        assert abs(total - 1.0) < 0.001

    def test_invalid_weights_raise(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            WeightConfig(skills=0.5, experience=0.5, location=0.5)

    def test_compute_overall(self) -> None:
        wc = WeightConfig()
        sc = ScoreComponents(
            skills=1.0,
            experience=1.0,
            location=1.0,
            salary=1.0,
            visa=1.0,
            remote=1.0,
            tech_stack=1.0,
            industry=1.0,
            culture=1.0,
            growth=1.0,
        )
        assert abs(wc.compute_overall(sc) - 1.0) < 0.001

    def test_compute_overall_zeros(self) -> None:
        wc = WeightConfig()
        sc = ScoreComponents()
        assert wc.compute_overall(sc) == 0.0

    def test_compute_overall_partial(self) -> None:
        wc = WeightConfig()
        sc = ScoreComponents(skills=0.5)
        expected = wc.skills * 0.5
        assert abs(wc.compute_overall(sc) - expected) < 0.001
