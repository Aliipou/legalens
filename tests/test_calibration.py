"""Tests for the calibrated risk model."""
import pytest
from app.diff.calibration import RiskCalibrator, calibrated_score, calibration_probs

_LEVELS = {"low", "medium", "high", "critical"}


def test_calibrator_loads():
    c = RiskCalibrator()
    assert c._levels == ["low", "medium", "high", "critical"]


def test_score_returns_valid_level():
    for sem, rule, struct in [(5, 0, 10), (30, 35, 40), (28, 85, 70), (5, 100, 100)]:
        score, level = calibrated_score(sem, rule, struct)
        assert 0 <= score <= 100
        assert level in _LEVELS


def test_calibration_probs_sum_to_one():
    probs = calibration_probs(28, 85, 70)
    assert abs(sum(probs.values()) - 1.0) < 0.01
    assert set(probs.keys()) == _LEVELS


def test_no_rules_low_similarity_stays_medium_or_below():
    # Big semantic shift but zero rule hits → not critical
    score, level = calibrated_score(80, 0, 10)
    assert level in ("low", "medium", "high")


def test_critical_rules_dominate():
    # CRITICAL rule score (35+35=70) + important section → critical
    score, level = calibrated_score(28, 85, 70)
    assert level == "critical"


def test_zero_inputs_low():
    score, level = calibrated_score(0, 0, 0)
    assert level in ("low", "medium")


def test_liability_shield_removed_critical():
    # liability shield removed: high structural (70), high rule score (35+)
    score, level = calibrated_score(5, 100, 100)
    assert level == "critical"


def test_score_is_monotone_in_rule_score():
    # More rule hits → higher or equal score
    _, l1 = calibrated_score(20, 10, 30)
    _, l2 = calibrated_score(20, 60, 30)
    level_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    assert level_rank[l2] >= level_rank[l1]


@pytest.mark.parametrize("sem,rule,struct,expected_min", [
    (5,   0,  10, "low"),
    (28, 85,  70, "critical"),
    (5, 100, 100, "critical"),
])
def test_anchor_cases(sem, rule, struct, expected_min):
    _, level = calibrated_score(sem, rule, struct)
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    assert rank[level] >= rank[expected_min]
