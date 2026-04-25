"""Hybrid risk scorer: calibrated model replaces hand-tuned weights."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.diff.rule_engine import RuleHit, RuleSeverity, rule_risk_score

_STRUCTURAL_BASE = {
    "preamble": 60,
    "section": 40,
    "clause": 30,
    "subclause": 20,
    "bullet": 10,
}

_CRITICAL_HEADING = re.compile(
    r"\b(liability|indemnif|terminat|payment|arbitrat|governing|confidential|assignment|penalty|damage)\b",
    re.IGNORECASE,
)


@dataclass
class RiskScore:
    semantic_score: float
    rule_score: int
    structural_score: int
    combined: float
    level: str
    drivers: list[str]
    calibration_probs: dict[str, float]


def _semantic_distance(similarity: float | None) -> float:
    if similarity is None:
        return 70.0
    return max(0.0, (1.0 - similarity) * 100.0)


def _structural_importance(node_type: str, heading: str | None) -> int:
    base = _STRUCTURAL_BASE.get(node_type, 30)
    if heading and _CRITICAL_HEADING.search(heading):
        base = min(base + 30, 100)
    return base


def _build_drivers(
    rule_hits: list[RuleHit],
    structural: int,
    similarity: float | None,
) -> list[str]:
    drivers: list[str] = []
    criticals = [h for h in rule_hits if h.severity == RuleSeverity.CRITICAL]
    highs = [h for h in rule_hits if h.severity == RuleSeverity.HIGH]
    for h in criticals[:3]:
        drivers.append(f"[CRITICAL] {h.description}")
    for h in highs[:2]:
        drivers.append(f"[HIGH] {h.description}")
    if len(rule_hits) > 5:
        drivers.append(f"... and {len(rule_hits) - 5} more rule hits")
    if similarity is not None and similarity < 0.75:
        drivers.append(f"Low semantic similarity ({similarity:.2f}) — substantial text rewrite")
    elif similarity is not None and similarity < 0.90:
        drivers.append(f"Moderate semantic shift (similarity={similarity:.2f})")
    if structural >= 60:
        drivers.append("High-importance clause position (liability/payment/termination section)")
    return drivers or ["Minor wording change"]


def compute(
    similarity: float | None,
    rule_hits: list[RuleHit],
    node_type: str = "clause",
    heading: str | None = None,
) -> RiskScore:
    from app.diff.calibration import calibrated_score, calibration_probs

    sem = _semantic_distance(similarity)
    rule = rule_risk_score(rule_hits)
    struct = _structural_importance(node_type, heading)

    combined, level = calibrated_score(sem, rule, struct)
    probs = calibration_probs(sem, rule, struct)

    return RiskScore(
        semantic_score=round(sem, 1),
        rule_score=rule,
        structural_score=struct,
        combined=combined,
        level=level,
        drivers=_build_drivers(rule_hits, struct, similarity),
        calibration_probs=probs,
    )
