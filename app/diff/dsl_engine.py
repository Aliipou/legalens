"""DSL rule engine: loads rules from YAML, evaluates structured conditions against text pairs."""
from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import yaml

from app.diff.rule_engine import RuleHit, RuleSeverity

_RULES_PATH = Path(__file__).parent.parent.parent / "rules" / "legal_rules.yaml"


class DSLRuleEngine:
    def __init__(self, rules_path: Path | str = _RULES_PATH) -> None:
        with open(rules_path) as f:
            cfg = yaml.safe_load(f)
        self._patterns: dict[str, re.Pattern] = {
            name: re.compile(pat, re.IGNORECASE)
            for name, pat in cfg.get("patterns", {}).items()
        }
        self._rules: list[dict] = cfg.get("rules", [])
        self._scope_terms: dict[str, list[str]] = cfg.get("scope_terms", {})

    # ── Public ────────────────────────────────────────────────────────────────

    def apply(self, old: str, new: str) -> list[RuleHit]:
        hits: list[RuleHit] = []
        for rule in self._rules:
            hit = self._eval_rule(rule, old, new)
            if hit:
                hits.append(hit)
        hits.extend(self._eval_scope_terms(old, new))
        return hits

    def rule_ids(self) -> list[str]:
        ids = [r["id"] for r in self._rules]
        for sev, terms in self._scope_terms.items():
            for t in terms:
                ids += [f"scope.{t}_added", f"scope.{t}_removed"]
        return ids

    # ── Rule evaluation ───────────────────────────────────────────────────────

    def _eval_rule(self, rule: dict, old: str, new: str) -> RuleHit | None:
        conditions = rule.get("conditions", [])
        match_mode = rule.get("match", "all")
        evidence: dict[str, Any] = {}

        results: list[bool] = []
        for cond in conditions:
            fired, ev = self._eval_condition(cond, old, new)
            evidence.update(ev)
            results.append(fired)

        matched = all(results) if match_mode == "all" else any(results)
        if not matched:
            return None

        severity_val = rule["severity"]
        if severity_val == "dynamic":
            severity_val = self._resolve_dynamic_severity(rule, evidence)

        # Render snippet templates before description so they use evidence
        snippet_tmpl = rule.get("snippet_template", {})
        if snippet_tmpl.get("old"):
            evidence.setdefault("old_snippet", _render(snippet_tmpl["old"], evidence))
        if snippet_tmpl.get("new"):
            evidence.setdefault("new_snippet", _render(snippet_tmpl["new"], evidence))

        return RuleHit(
            rule_id=rule["id"],
            severity=RuleSeverity(severity_val),
            description=_render(rule["description"], evidence),
            old_snippet=evidence.get("old_snippet") or evidence.get("old_match"),
            new_snippet=evidence.get("new_snippet") or evidence.get("new_match"),
        )

    def _eval_condition(self, cond: dict, old: str, new: str) -> tuple[bool, dict[str, Any]]:
        op = cond["op"]
        pattern_name = cond.get("pattern")
        p = self._patterns[pattern_name] if pattern_name else None
        ev: dict[str, Any] = {}

        if op == "pattern_added":
            assert p is not None
            old_m = p.findall(old)
            new_m = p.findall(new)
            ev["old_match"] = _first(old_m)
            ev["new_match"] = _first(new_m)
            return (not bool(old_m) and bool(new_m)), ev

        if op == "pattern_removed":
            assert p is not None
            old_m = p.findall(old)
            new_m = p.findall(new)
            ev["old_match"] = _first(old_m)
            ev["new_match"] = _first(new_m)
            return (bool(old_m) and not bool(new_m)), ev

        if op == "pattern_in_old":
            assert p is not None
            return bool(p.search(old)), ev

        if op == "pattern_in_new":
            assert p is not None
            return bool(p.search(new)), ev

        if op == "pattern_in_both":
            assert p is not None
            return bool(p.search(old)) and bool(p.search(new)), ev

        if op == "count_was_positive":
            assert p is not None
            c = len(p.findall(old))
            ev["old_count"] = c
            return c > 0, ev

        if op == "count_is_zero":
            assert p is not None
            c = len(p.findall(new))
            ev["new_count"] = c
            return c == 0, ev

        if op == "count_is_positive":
            assert p is not None
            c = len(p.findall(new))
            ev["new_count"] = c
            return c > 0, ev

        if op == "count_was_zero":
            assert p is not None
            c = len(p.findall(old))
            ev["old_count"] = c
            return c == 0, ev

        if op == "count_increased":
            assert p is not None
            oc = len(p.findall(old))
            nc = len(p.findall(new))
            ev["old_count"] = oc
            ev["new_count"] = nc
            return nc > oc, ev

        if op == "count_decreased":
            assert p is not None
            oc = len(p.findall(old))
            nc = len(p.findall(new))
            ev["old_count"] = oc
            ev["new_count"] = nc
            return nc < oc, ev

        if op == "count_delta_ge":
            assert p is not None
            threshold = cond.get("threshold", 1)
            oc = len(p.findall(old))
            nc = len(p.findall(new))
            ev["old_count"] = oc
            ev["new_count"] = nc
            return abs(nc - oc) >= threshold, ev

        if op == "numeric_max_changed":
            assert p is not None
            old_nums = _extract_numbers(p, old)
            new_nums = _extract_numbers(p, new)
            if not old_nums or not new_nums:
                return False, ev
            old_max = max(old_nums)
            new_max = max(new_nums)
            ev["old_max"] = int(old_max)
            ev["new_max"] = int(new_max)
            ev["direction"] = "extended" if new_max > old_max else "shortened"
            return old_max != new_max, ev

        if op == "amounts_set_differ":
            pattern_names = cond.get("patterns", [pattern_name])
            old_set: set[str] = set()
            new_set: set[str] = set()
            for pn in pattern_names:
                old_set.update(_findall_str(self._patterns[pn], old))
                new_set.update(_findall_str(self._patterns[pn], new))
            added = new_set - old_set
            removed = old_set - new_set
            ev["old_snippet"] = ", ".join(sorted(removed)) or None
            ev["new_snippet"] = ", ".join(sorted(added)) or None
            return bool(added or removed), ev

        if op == "context_changed":
            assert p is not None
            ctx = cond.get("context_chars", 80)
            return p.sub("\u00a7", old)[:ctx] != p.sub("\u00a7", new)[:ctx], ev

        raise ValueError(f"Unknown DSL condition op: {op!r}")

    @staticmethod
    def _resolve_dynamic_severity(rule: dict, evidence: dict) -> str:
        srv = rule.get("severity_rule", {})
        if srv.get("type") == "numeric_max_delta":
            old_max = evidence.get("old_max", 0)
            new_max = evidence.get("new_max", 0)
            delta = abs(new_max - old_max)
            for t in srv.get("thresholds", []):
                if "delta_gt" in t and delta > t["delta_gt"]:
                    return t["severity"]
                if "default" in t:
                    return t["default"]
        return "medium"

    def _eval_scope_terms(self, old: str, new: str) -> list[RuleHit]:
        sev_map: dict[str, str] = {}
        all_terms: list[str] = []
        for sev, terms in self._scope_terms.items():
            for term in terms:
                sev_map[term.lower()] = sev
                all_terms.append(term)
        if not all_terms:
            return []

        pattern = re.compile(
            r"\b(" + "|".join(re.escape(t) for t in all_terms) + r")\b",
            re.IGNORECASE,
        )
        old_ex = {m.lower() for m in pattern.findall(old)}
        new_ex = {m.lower() for m in pattern.findall(new)}

        hits: list[RuleHit] = []
        for term in sorted(new_ex - old_ex):
            hits.append(RuleHit(
                rule_id=f"scope.{term}_added",
                severity=RuleSeverity(sev_map.get(term, "medium")),
                description=f"'{term}' added — scope/irrevocability change.",
                new_snippet=term,
            ))
        for term in sorted(old_ex - new_ex):
            hits.append(RuleHit(
                rule_id=f"scope.{term}_removed",
                severity=RuleSeverity.MEDIUM,
                description=f"'{term}' removed.",
                old_snippet=term,
            ))
        return hits


# ── Module-level singleton ────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _engine() -> DSLRuleEngine:
    return DSLRuleEngine()


def apply_rules_dsl(old: str, new: str) -> list[RuleHit]:
    return _engine().apply(old, new)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render(template: str, evidence: dict) -> str:
    try:
        return template.format(**evidence)
    except (KeyError, ValueError):
        return template


def _first(matches: list) -> str | None:
    if not matches:
        return None
    m = matches[0]
    if isinstance(m, tuple):
        return m[0] if m else None
    return str(m)


def _extract_numbers(p: re.Pattern, text: str) -> list[float]:
    nums = []
    for m in p.findall(text):
        s = m if isinstance(m, str) else (m[0] if isinstance(m, tuple) and m else "")
        try:
            nums.append(float(s.replace(",", "")))
        except (ValueError, AttributeError):
            pass
    return nums


def _findall_str(p: re.Pattern, text: str) -> set[str]:
    result = set()
    for m in p.findall(text):
        if isinstance(m, str):
            result.add(m)
        elif isinstance(m, tuple):
            result.add(m[0] if m else "")
    return result
