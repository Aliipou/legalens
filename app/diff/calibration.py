"""Calibrated risk model: logistic regression trained on annotated anchor cases.

Inference uses only numpy — no sklearn required at runtime.
Re-train by running:  python scripts/calibrate.py
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

import numpy as np

_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "calibration.json"


class RiskCalibrator:
    """Wraps a serialised logistic-regression model for zero-dependency inference."""

    def __init__(self, model_path: Path | str = _MODEL_PATH) -> None:
        with open(model_path) as f:
            m = json.load(f)
        self._mean = np.array(m["scaler_mean"], dtype=float)
        self._scale = np.array(m["scaler_scale"], dtype=float)
        self._coef = np.array(m["coef"], dtype=float)         # (n_classes, 3)
        self._intercept = np.array(m["intercept"], dtype=float)
        self._levels: list[str] = m["levels"]
        self._midpoints = np.array(m["level_midpoints"], dtype=float)

    def score(self, semantic: float, rule: int, structural: int) -> tuple[float, str]:
        """Return (calibrated_score 0-100, risk_level)."""
        probs = self._probs(semantic, rule, structural)
        level = self._levels[int(probs.argmax())]
        calibrated = float(probs @ self._midpoints)
        return round(calibrated, 1), level

    def probabilities(self, semantic: float, rule: int, structural: int) -> dict[str, float]:
        """Per-class probabilities — useful for reasoning graph confidence."""
        probs = self._probs(semantic, rule, structural)
        return {lvl: round(float(p), 3) for lvl, p in zip(self._levels, probs)}

    def _probs(self, semantic: float, rule: int, structural: int) -> np.ndarray:
        x = (np.array([semantic, rule, structural], dtype=float) - self._mean) / self._scale
        logits = self._coef @ x + self._intercept
        e = np.exp(logits - logits.max())
        return e / e.sum()


@functools.lru_cache(maxsize=1)
def _calibrator() -> RiskCalibrator:
    return RiskCalibrator()


def calibrated_score(
    semantic: float, rule: int, structural: int
) -> tuple[float, str]:
    """Convenience wrapper used by risk_scorer."""
    return _calibrator().score(semantic, rule, structural)


def calibration_probs(
    semantic: float, rule: int, structural: int
) -> dict[str, float]:
    return _calibrator().probabilities(semantic, rule, structural)
