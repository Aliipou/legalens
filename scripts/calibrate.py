"""
Fit a logistic-regression risk calibrator on annotated anchor examples.

Usage:
    python scripts/calibrate.py
Writes: models/calibration.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# fmt: off
# Annotated anchor cases: [semantic_score, rule_score, structural_score, label]
# Labels: 0=low  1=medium  2=high  3=critical
#
# semantic_score  = (1 - cosine_similarity) * 100   (0=identical, 100=opposite)
# rule_score      = sum of severity weights, capped at 100
# structural_score = 10-100 based on clause position + heading keywords
ANCHORS: list[tuple[float, int, int, int]] = [
    # ── low ──────────────────────────────────────────────────────────────────
    ( 5,  0, 10, 0),   # near-identical texts, no rules
    (10,  3, 10, 0),   # minor wording + single LOW hit
    (14,  0, 20, 0),   # small semantic shift, no legal rules
    ( 8,  0, 30, 0),   # minor section rewrite
    (12,  3, 10, 0),   # formatting change with trivial hit
    # ── medium ───────────────────────────────────────────────────────────────
    (30, 10, 20, 1),   # moderate rewrite + LOW hit
    (50,  0, 10, 1),   # large semantic shift but zero legal rules
    (22, 10, 40, 1),   # MEDIUM hit in mid-importance section
    (42,  0, 30, 1),   # substantial rewrite, no rules
    (26, 10, 30, 1),   # deadline shortened 7 days (MEDIUM hit)
    # ── high ─────────────────────────────────────────────────────────────────
    (22, 20, 40, 2),   # jurisdiction changed (HIGH)
    (30, 35, 30, 2),   # single CRITICAL hit, low structural weight
    (26, 20, 60, 2),   # HIGH rule in important section
    (72, 20, 30, 2),   # big rewrite + MEDIUM/HIGH rules
    (42, 40, 50, 2),   # multiple HIGH hits
    (90, 35, 40, 2),   # complete rewrite + single CRITICAL (semantic dominates)
    # ── critical ─────────────────────────────────────────────────────────────
    (28, 85, 70, 3),   # shall→may + deadline ext. in payment section
    ( 5,100,100, 3),   # liability shield removed in liability section
    (35, 70, 70, 3),   # CRITICAL + HIGH hits in important section
    (52, 55, 80, 3),   # multiple hits + highest-importance section
    (22, 35, 90, 3),   # CRITICAL rule + maximum structural importance
    (18, 55, 60, 3),   # arbitration added + jurisdiction change
]
# fmt: on


def train(anchors: list[tuple[float, int, int, int]], out_path: Path) -> None:
    X = np.array([[s, r, st] for s, r, st, _ in anchors], dtype=float)
    y = np.array([label for *_, label in anchors])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = LogisticRegression(
        multi_class="multinomial",
        solver="lbfgs",
        max_iter=1000,
        C=1.0,
        random_state=42,
    )
    clf.fit(X_scaled, y)

    acc = (clf.predict(X_scaled) == y).mean()
    print(f"Training accuracy on {len(anchors)} anchors: {acc:.0%}")

    model = {
        "calibration_version": "1.0",
        "levels": ["low", "medium", "high", "critical"],
        "level_midpoints": [10, 32, 57, 85],
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coef": clf.coef_.tolist(),
        "intercept": clf.intercept_.tolist(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(model, f, indent=2)
    print(f"Saved calibration model -> {out_path}")


if __name__ == "__main__":
    train(ANCHORS, Path(__file__).parent.parent / "models" / "calibration.json")
