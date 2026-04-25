"""Tests for the YAML DSL rule engine."""
import pytest
from app.diff.dsl_engine import DSLRuleEngine, _engine
from app.diff.rule_engine import RuleSeverity


@pytest.fixture(autouse=True)
def fresh_engine():
    _engine.cache_clear()
    yield


engine = DSLRuleEngine()


# ── Condition ops ─────────────────────────────────────────────────────────────

def test_pattern_added():
    hits = engine.apply("Party A retains rights.", "Party A hereby waives all rights.")
    ids = [h.rule_id for h in hits]
    assert "rights.waiver_added" in ids


def test_pattern_removed():
    hits = engine.apply("Company shall not be liable.", "Company accepts all liability.")
    ids = [h.rule_id for h in hits]
    assert "liability.shield_removed" in ids


def test_count_was_positive_and_count_is_zero():
    old = "Party shall pay."
    new = "Party may pay."
    hits = engine.apply(old, new)
    assert any(h.rule_id == "obligation.shall_to_may" for h in hits)


def test_count_increased():
    old = "Party may pay."
    new = "Party shall deliver and shall pay and shall report."
    hits = engine.apply(old, new)
    assert any(h.rule_id == "obligation.may_to_shall" for h in hits)


def test_count_delta_ge():
    old = "Liability arises from breach."
    new = "No liability, no liability cap, and all liability is excluded."
    hits = engine.apply(old, new)
    ids = [h.rule_id for h in hits]
    assert "liability.frequency_change" in ids


def test_numeric_max_changed_and_snippet():
    hits = engine.apply(
        "Payment is due within 30 days.",
        "Payment is due within 90 days.",
    )
    hit = next((h for h in hits if h.rule_id == "deadline.changed"), None)
    assert hit is not None
    assert "30" in (hit.old_snippet or "")
    assert "90" in (hit.new_snippet or "")


def test_amounts_set_differ():
    hits = engine.apply("Fee is $10,000.", "Fee is $50,000.")
    assert any(h.rule_id == "penalty.amount_change" for h in hits)


def test_percent_change():
    hits = engine.apply("Rate is 2%.", "Rate is 15%.")
    assert any(h.rule_id == "penalty.amount_change" for h in hits)


def test_pattern_in_both_and_context_changed():
    hits = engine.apply(
        "Disputes shall be resolved by the courts of Finland.",
        "Disputes shall be resolved by the courts of New York.",
    )
    assert any(h.rule_id == "dispute.jurisdiction_changed" for h in hits)


def test_no_hit_when_unchanged():
    text = "Party A shall pay $10,000 within 30 days."
    hits = engine.apply(text, text)
    assert hits == []


# ── Dynamic severity ──────────────────────────────────────────────────────────

def test_dynamic_severity_high_for_large_delta():
    hits = engine.apply("Deliver within 10 days.", "Deliver within 90 days.")
    hit = next(h for h in hits if h.rule_id == "deadline.changed")
    assert hit.severity == RuleSeverity.HIGH


def test_dynamic_severity_medium_for_small_delta():
    hits = engine.apply("Deliver within 30 days.", "Deliver within 38 days.")
    hit = next(h for h in hits if h.rule_id == "deadline.changed")
    assert hit.severity == RuleSeverity.MEDIUM


# ── Scope terms (dynamic rule IDs) ────────────────────────────────────────────

def test_scope_irrevocable_added_critical():
    hits = engine.apply("A license is granted.", "An irrevocable license is granted.")
    hit = next((h for h in hits if "irrevocable" in h.rule_id and "added" in h.rule_id), None)
    assert hit is not None
    assert hit.severity == RuleSeverity.CRITICAL


def test_scope_perpetual_added_critical():
    hits = engine.apply("Rights are granted.", "Perpetual rights are granted.")
    hit = next((h for h in hits if "perpetual" in h.rule_id), None)
    assert hit is not None
    assert hit.severity == RuleSeverity.CRITICAL


def test_scope_exclusive_added_high():
    hits = engine.apply("Non-exclusive license.", "Exclusive license.")
    hit = next((h for h in hits if "exclusive" in h.rule_id and "added" in h.rule_id), None)
    assert hit is not None
    assert hit.severity == RuleSeverity.HIGH


def test_scope_term_removed_medium():
    hits = engine.apply("An irrevocable license.", "A license.")
    hit = next((h for h in hits if "irrevocable" in h.rule_id and "removed" in h.rule_id), None)
    assert hit is not None
    assert hit.severity == RuleSeverity.MEDIUM


# ── Severity correctness ──────────────────────────────────────────────────────

def test_arbitration_added_critical():
    hits = engine.apply("Disputes go to court.", "Disputes go to arbitration.")
    hit = next(h for h in hits if h.rule_id == "dispute.arbitration_added")
    assert hit.severity == RuleSeverity.CRITICAL


def test_waiver_added_critical():
    hits = engine.apply("Party A keeps rights.", "Party A waives all rights.")
    hit = next(h for h in hits if h.rule_id == "rights.waiver_added")
    assert hit.severity == RuleSeverity.CRITICAL


def test_indemnity_added_high():
    hits = engine.apply("Service provided.", "Service provided with indemnification.")
    hit = next((h for h in hits if h.rule_id == "rights.indemnity_added"), None)
    assert hit is not None
    assert hit.severity == RuleSeverity.HIGH


# ── DSL introspection ─────────────────────────────────────────────────────────

def test_rule_ids_are_strings():
    ids = engine.rule_ids()
    assert len(ids) > 15
    assert all(isinstance(i, str) for i in ids)
    assert "obligation.shall_to_may" in ids
