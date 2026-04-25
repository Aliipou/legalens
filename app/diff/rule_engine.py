"""Legal rule engine — detects specific obligation/liability/deadline changes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class RuleSeverity(str, Enum):
    CRITICAL = "critical"   # changes core obligation or liability
    HIGH = "high"           # significant financial/legal impact
    MEDIUM = "medium"       # process/procedure change
    LOW = "low"             # minor wording shift


@dataclass
class RuleHit:
    rule_id: str
    severity: RuleSeverity
    description: str
    old_snippet: str | None = None
    new_snippet: str | None = None


# ── Individual rule detectors ─────────────────────────────────────────────────

def _find_all(pattern: re.Pattern, text: str) -> list[str]:
    return pattern.findall(text)


_SHALL_MAY = re.compile(r"\bshall\b", re.IGNORECASE)
_MAY = re.compile(r"\bmay\b", re.IGNORECASE)
_MUST = re.compile(r"\bmust\b", re.IGNORECASE)

_LIABILITY_SHIELD = re.compile(
    r"\b(not\s+(?:be\s+)?liable|no\s+liability|limit(?:ed|ation)\s+of\s+liability"
    r"|exclude[sd]?\s+(?:all\s+)?liability|liability\s+(?:cap|ceiling|limit))\b",
    re.IGNORECASE,
)
_LIABILITY_GENERAL = re.compile(r"\bliabilit(?:y|ies)\b", re.IGNORECASE)

_PENALTY = re.compile(
    r"\b(penalt(?:y|ies)|liquidated\s+damages?|damages?|fine[sd]?|forfeit(?:ure)?)\b",
    re.IGNORECASE,
)

_AMOUNT = re.compile(
    r"(?:\$|€|£|USD|EUR|GBP)\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|k))?",
    re.IGNORECASE,
)
_PERCENT = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")

_DEADLINE = re.compile(
    r"\b(\d+)\s*(?:calendar\s+)?(?:business\s+)?days?\b",
    re.IGNORECASE,
)

_ARBITRATION = re.compile(
    r"\b(arbitrat(?:ion|e|or)|mediat(?:ion|e)|dispute\s+resolution)\b",
    re.IGNORECASE,
)
_JURISDICTION = re.compile(
    r"\b(jurisdict(?:ion|s)|governing\s+law|venue|choice\s+of\s+law|courts?\s+of)\b",
    re.IGNORECASE,
)

_EXCLUSIVITY = re.compile(
    r"\b(exclusive|non-exclusive|sole(?:ly)?|irrevocable|perpetual|world[- ]?wide)\b",
    re.IGNORECASE,
)

_WAIVER = re.compile(r"\b(waiv(?:er|e|ed)|relinquish|forfeit)\b", re.IGNORECASE)
_INDEMNITY = re.compile(r"\bindemnif(?:y|ication|ied|ies)\b", re.IGNORECASE)
_TERMINATION = re.compile(r"\bterminat(?:e|ion|ed)\b", re.IGNORECASE)
_ASSIGNMENT = re.compile(r"\bassign(?:ment|able|ed|s)?\b", re.IGNORECASE)
_CONFIDENTIAL = re.compile(r"\bconfidential(?:ity|)\b", re.IGNORECASE)
_FORCE_MAJEURE = re.compile(r"\bforce\s+majeure\b", re.IGNORECASE)


def _obligation_shift(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_shall = len(_SHALL_MAY.findall(old))
    new_shall = len(_SHALL_MAY.findall(new))
    old_may = len(_MAY.findall(old))
    new_may = len(_MAY.findall(new))

    if old_shall > 0 and new_shall == 0 and new_may > old_may:
        hits.append(RuleHit(
            rule_id="obligation.shall_to_may",
            severity=RuleSeverity.CRITICAL,
            description="Mandatory obligation ('shall') replaced with discretionary language ('may') — obligation weakened.",
            old_snippet=f"shall ({old_shall}x)",
            new_snippet=f"may ({new_may}x)",
        ))
    elif new_shall > old_shall:
        hits.append(RuleHit(
            rule_id="obligation.may_to_shall",
            severity=RuleSeverity.HIGH,
            description="Discretionary 'may' replaced with mandatory 'shall' — obligation strengthened.",
            old_snippet=f"shall ({old_shall}x)",
            new_snippet=f"shall ({new_shall}x)",
        ))
    return hits


def _liability_changes(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_shields = _LIABILITY_SHIELD.findall(old)
    new_shields = _LIABILITY_SHIELD.findall(new)

    if old_shields and not new_shields:
        hits.append(RuleHit(
            rule_id="liability.shield_removed",
            severity=RuleSeverity.CRITICAL,
            description="Liability limitation/exclusion clause removed — party may now bear unlimited liability.",
            old_snippet=old_shields[0],
        ))
    elif not old_shields and new_shields:
        hits.append(RuleHit(
            rule_id="liability.shield_added",
            severity=RuleSeverity.HIGH,
            description="New liability limitation/exclusion added.",
            new_snippet=new_shields[0],
        ))

    old_liability = len(_LIABILITY_GENERAL.findall(old))
    new_liability = len(_LIABILITY_GENERAL.findall(new))
    if abs(old_liability - new_liability) >= 2:
        hits.append(RuleHit(
            rule_id="liability.frequency_change",
            severity=RuleSeverity.MEDIUM,
            description=f"Significant change in liability references: {old_liability} → {new_liability}.",
        ))
    return hits


def _penalty_changes(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_penalty = _PENALTY.findall(old)
    new_penalty = _PENALTY.findall(new)

    if not old_penalty and new_penalty:
        hits.append(RuleHit(
            rule_id="penalty.added",
            severity=RuleSeverity.HIGH,
            description=f"Penalty/damages clause added: {new_penalty[0]}.",
            new_snippet=new_penalty[0],
        ))
    elif old_penalty and not new_penalty:
        hits.append(RuleHit(
            rule_id="penalty.removed",
            severity=RuleSeverity.MEDIUM,
            description="Penalty/damages clause removed.",
            old_snippet=old_penalty[0],
        ))

    # Amount changes
    old_amounts = _AMOUNT.findall(old) + _PERCENT.findall(old)
    new_amounts = _AMOUNT.findall(new) + _PERCENT.findall(new)
    old_set = set(str(a) for a in old_amounts)
    new_set = set(str(a) for a in new_amounts)
    added_amounts = new_set - old_set
    removed_amounts = old_set - new_set
    if added_amounts or removed_amounts:
        hits.append(RuleHit(
            rule_id="penalty.amount_change",
            severity=RuleSeverity.HIGH,
            description="Financial amounts changed.",
            old_snippet=", ".join(removed_amounts) or None,
            new_snippet=", ".join(added_amounts) or None,
        ))
    return hits


def _deadline_changes(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_days = [int(d) for d in _DEADLINE.findall(old)]
    new_days = [int(d) for d in _DEADLINE.findall(new)]

    if old_days and new_days:
        old_max = max(old_days)
        new_max = max(new_days)
        if old_max != new_max:
            direction = "extended" if new_max > old_max else "shortened"
            severity = RuleSeverity.MEDIUM if abs(new_max - old_max) <= 15 else RuleSeverity.HIGH
            hits.append(RuleHit(
                rule_id="deadline.changed",
                severity=severity,
                description=f"Deadline {direction}: {old_max} → {new_max} days.",
                old_snippet=f"{old_max} days",
                new_snippet=f"{new_max} days",
            ))
    elif not old_days and new_days:
        hits.append(RuleHit(
            rule_id="deadline.added",
            severity=RuleSeverity.MEDIUM,
            description=f"Time constraint added: {new_days[0]} days.",
        ))
    elif old_days and not new_days:
        hits.append(RuleHit(
            rule_id="deadline.removed",
            severity=RuleSeverity.MEDIUM,
            description="Time constraint removed — no deadline now specified.",
        ))
    return hits


def _arbitration_jurisdiction(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_arb = bool(_ARBITRATION.search(old))
    new_arb = bool(_ARBITRATION.search(new))
    if not old_arb and new_arb:
        hits.append(RuleHit(
            rule_id="dispute.arbitration_added",
            severity=RuleSeverity.CRITICAL,
            description="Arbitration/dispute resolution clause added — may waive right to court proceedings.",
        ))
    elif old_arb and not new_arb:
        hits.append(RuleHit(
            rule_id="dispute.arbitration_removed",
            severity=RuleSeverity.HIGH,
            description="Arbitration clause removed.",
        ))

    old_jur = bool(_JURISDICTION.search(old))
    new_jur = bool(_JURISDICTION.search(new))
    if old_jur and new_jur:
        # Check if the jurisdiction text changed significantly
        old_j_ctx = _JURISDICTION.sub("§", old)
        new_j_ctx = _JURISDICTION.sub("§", new)
        if old_j_ctx[:80] != new_j_ctx[:80]:
            hits.append(RuleHit(
                rule_id="dispute.jurisdiction_changed",
                severity=RuleSeverity.HIGH,
                description="Governing law/jurisdiction clause modified.",
            ))
    return hits


def _exclusivity_scope(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_ex = set(m.lower() for m in _EXCLUSIVITY.findall(old))
    new_ex = set(m.lower() for m in _EXCLUSIVITY.findall(new))
    added = new_ex - old_ex
    removed = old_ex - new_ex
    critical_terms = {"irrevocable", "perpetual", "irrevocably"}
    high_terms = {"exclusive", "solely", "sole", "worldwide", "world-wide"}
    for term in added:
        sev = RuleSeverity.CRITICAL if term in critical_terms else RuleSeverity.HIGH if term in high_terms else RuleSeverity.MEDIUM
        hits.append(RuleHit(
            rule_id=f"scope.{term}_added",
            severity=sev,
            description=f"'{term}' added — scope/irrevocability change.",
            new_snippet=term,
        ))
    for term in removed:
        hits.append(RuleHit(
            rule_id=f"scope.{term}_removed",
            severity=RuleSeverity.MEDIUM,
            description=f"'{term}' removed.",
            old_snippet=term,
        ))
    return hits


def _waiver_indemnity(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_waiv = bool(_WAIVER.search(old))
    new_waiv = bool(_WAIVER.search(new))
    if not old_waiv and new_waiv:
        hits.append(RuleHit(
            rule_id="rights.waiver_added",
            severity=RuleSeverity.CRITICAL,
            description="Waiver of rights added.",
        ))
    old_ind = bool(_INDEMNITY.search(old))
    new_ind = bool(_INDEMNITY.search(new))
    if not old_ind and new_ind:
        hits.append(RuleHit(
            rule_id="rights.indemnity_added",
            severity=RuleSeverity.HIGH,
            description="Indemnification obligation added.",
        ))
    elif old_ind and not new_ind:
        hits.append(RuleHit(
            rule_id="rights.indemnity_removed",
            severity=RuleSeverity.HIGH,
            description="Indemnification clause removed.",
        ))
    return hits


def _termination_rights(old: str, new: str) -> list[RuleHit]:
    hits = []
    old_term = bool(_TERMINATION.search(old))
    new_term = bool(_TERMINATION.search(new))
    if not old_term and new_term:
        hits.append(RuleHit(
            rule_id="term.termination_added",
            severity=RuleSeverity.HIGH,
            description="Termination clause added.",
        ))
    elif old_term and not new_term:
        hits.append(RuleHit(
            rule_id="term.termination_removed",
            severity=RuleSeverity.HIGH,
            description="Termination clause removed — exit rights unclear.",
        ))
    return hits


# ── Public interface ──────────────────────────────────────────────────────────

_RULES = [
    _obligation_shift,
    _liability_changes,
    _penalty_changes,
    _deadline_changes,
    _arbitration_jurisdiction,
    _exclusivity_scope,
    _waiver_indemnity,
    _termination_rights,
]


def apply_rules(old_text: str, new_text: str) -> list[RuleHit]:
    """Run all legal rules against a pair of clause texts."""
    hits: list[RuleHit] = []
    for rule_fn in _RULES:
        hits.extend(rule_fn(old_text, new_text))
    return hits


def rule_risk_score(hits: list[RuleHit]) -> int:
    """Convert rule hits to a 0-100 integer risk score."""
    weights = {
        RuleSeverity.CRITICAL: 35,
        RuleSeverity.HIGH: 20,
        RuleSeverity.MEDIUM: 10,
        RuleSeverity.LOW: 3,
    }
    score = sum(weights.get(h.severity, 0) for h in hits)
    return min(score, 100)
