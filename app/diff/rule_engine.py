"""Legal rule engine — public API delegates to the YAML DSL engine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuleSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RuleHit:
    rule_id: str
    severity: RuleSeverity
    description: str
    old_snippet: str | None = None
    new_snippet: str | None = None


# Severity → raw contribution toward a 0-100 rule score.
_SEVERITY_WEIGHT = {
    RuleSeverity.CRITICAL: 35,
    RuleSeverity.HIGH: 20,
    RuleSeverity.MEDIUM: 10,
    RuleSeverity.LOW: 3,
}


def apply_rules(old_text: str, new_text: str) -> list[RuleHit]:
    """Run all DSL-defined legal rules against a clause pair."""
    from app.diff.dsl_engine import apply_rules_dsl
    return apply_rules_dsl(old_text, new_text)


def rule_risk_score(hits: list[RuleHit]) -> int:
    """Sum severity weights, capped at 100."""
    return min(sum(_SEVERITY_WEIGHT.get(h.severity, 0) for h in hits), 100)
