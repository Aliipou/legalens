"""Hybrid risk scorer combining semantic + rule-based + structural signals."""
from __future__ import annotations

from dataclasses import dataclass

from app.diff.rule_engine import RuleHit, RuleSeverity, rule_risk_score


@dataclass
class RiskScore:
    semantic_score: float        # 0-100: distance from perfect similarity
    rule_score: int              # 0-100: from rule hits
    structural_score: int        # 0-100: positional importance
    combined: float              # 0-100: weighted final score
    level: str                   # "critical" | "high" | "medium" | "low"
    drivers: list[str]           # human-readable explanations


_WEIGHTS = {
    "semantic": 0.30,
    "rule": 0.55,
    "structural": 0.15,
}

_STRUCTURAL_IMPORTANCE = {
    "preamble": 60,
    "section": 40,
    "clause": 30,
    "subclause": 20,
    "bullet": 10,
}

def _semantic_distance(similarity: float | None) -> float:
    """Convert cosine similarity to a 0-100 risk signal (lower sim = higher risk)."""
    if similarity is None:
        return 70.0
    return max(0.0, (1.0 - similarity) * 100.0)


def _structural_importance(node_type: str, heading: str | None) -> int:
    import re
    base = _STRUCTURAL_IMPORTANCE.get(node_type, 30)
    if heading:
        critical_re = re.compile(
            r"\b(liability|indemnif|terminat|payment|arbitrat|governing|confidential|assignment|penalty|damage)\b",
            re.IGNORECASE,
        )
        if critical_re.search(heading):
            base = min(base + 30, 100)
    return base


def _level_from_score(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def _build_drivers(
    semantic: float,
    rule_hits: list[RuleHit],
    structural: int,
    similarity: float | None,
) -> list[str]:
    drivers = []

    if rule_hits:
        criticals = [h for h in rule_hits if h.severity == RuleSeverity.CRITICAL]
        highs = [h for h in rule_hits if h.severity == RuleSeverity.HIGH]
        for h in criticals[:3]:
            drivers.append(f"[CRITICAL] {h.description}")
        for h in highs[:2]:
            drivers.append(f"[HIGH] {h.description}")
        if len(rule_hits) > 5:
            drivers.append(f"… and {len(rule_hits) - 5} more rule hits")

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
    sem = _semantic_distance(similarity)
    rule = rule_risk_score(rule_hits)
    struct = _structural_importance(node_type, heading)

    combined = (
        sem * _WEIGHTS["semantic"]
        + rule * _WEIGHTS["rule"]
        + struct * _WEIGHTS["structural"]
    )

    return RiskScore(
        semantic_score=round(sem, 1),
        rule_score=rule,
        structural_score=struct,
        combined=round(combined, 1),
        level=_level_from_score(combined),
        drivers=_build_drivers(sem, rule_hits, struct, similarity),
    )
