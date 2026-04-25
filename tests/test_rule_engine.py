"""Tests for legal rule engine — obligation, liability, deadline, arbitration, etc."""
import pytest
from app.diff.rule_engine import apply_rules, rule_risk_score, RuleSeverity


# ── Obligation shift ───────────────────────────────────────────────────────────

def test_shall_to_may_detected():
    old = "Party A shall deliver the goods within 30 days."
    new = "Party A may deliver the goods within 30 days."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "obligation.shall_to_may" in ids
    hit = next(h for h in hits if h.rule_id == "obligation.shall_to_may")
    assert hit.severity == RuleSeverity.CRITICAL


def test_no_obligation_shift_when_unchanged():
    text = "Party A shall deliver within 30 days."
    hits = apply_rules(text, text)
    obligation_hits = [h for h in hits if "obligation" in h.rule_id]
    assert len(obligation_hits) == 0


# ── Liability ─────────────────────────────────────────────────────────────────

def test_liability_shield_removed():
    old = "Company shall not be liable for any indirect damages."
    new = "Company acknowledges its responsibility for all damages."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "liability.shield_removed" in ids
    hit = next(h for h in hits if h.rule_id == "liability.shield_removed")
    assert hit.severity == RuleSeverity.CRITICAL


def test_liability_shield_added():
    old = "Company is responsible for all damages."
    new = "Company shall not be liable for indirect or consequential damages."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "liability.shield_added" in ids


# ── Penalties ─────────────────────────────────────────────────────────────────

def test_penalty_clause_added():
    old = "Payment shall be made within 30 days."
    new = "Payment shall be made within 30 days. Late payment incurs a 5% penalty per month."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert any("penalty" in i for i in ids)


def test_amount_change_detected():
    old = "The fee shall be $10,000 per month."
    new = "The fee shall be $50,000 per month."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "penalty.amount_change" in ids


def test_percentage_change_detected():
    old = "Late payments incur a 2% interest rate."
    new = "Late payments incur a 15% interest rate."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "penalty.amount_change" in ids


# ── Deadlines ─────────────────────────────────────────────────────────────────

def test_deadline_extension():
    old = "Payment is due within 30 days of invoice."
    new = "Payment is due within 90 days of invoice."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "deadline.changed" in ids
    hit = next(h for h in hits if h.rule_id == "deadline.changed")
    assert "30" in hit.old_snippet
    assert "90" in hit.new_snippet


def test_deadline_shortening():
    old = "Notice shall be given 90 days in advance."
    new = "Notice shall be given 14 days in advance."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "deadline.changed" in ids


def test_deadline_added():
    old = "Party shall deliver the report."
    new = "Party shall deliver the report within 30 days."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "deadline.added" in ids


# ── Arbitration ───────────────────────────────────────────────────────────────

def test_arbitration_added():
    old = "Disputes shall be resolved in court."
    new = "All disputes shall be submitted to binding arbitration under ICC rules."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "dispute.arbitration_added" in ids
    hit = next(h for h in hits if h.rule_id == "dispute.arbitration_added")
    assert hit.severity == RuleSeverity.CRITICAL


def test_arbitration_removed():
    old = "Disputes shall be resolved by arbitration."
    new = "Disputes shall be resolved in competent courts."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "dispute.arbitration_removed" in ids


# ── Exclusivity / scope ───────────────────────────────────────────────────────

def test_irrevocable_added():
    old = "Company grants a license to use the software."
    new = "Company grants an irrevocable, perpetual license to use the software."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert any("irrevocable" in i or "perpetual" in i for i in ids)
    severities = [h.severity for h in hits if "irrevocable" in h.rule_id or "perpetual" in h.rule_id]
    assert RuleSeverity.CRITICAL in severities


# ── Waiver & indemnity ────────────────────────────────────────────────────────

def test_waiver_added():
    old = "Party A retains all rights."
    new = "Party A hereby waives all rights to claim damages."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "rights.waiver_added" in ids
    hit = next(h for h in hits if h.rule_id == "rights.waiver_added")
    assert hit.severity == RuleSeverity.CRITICAL


def test_indemnity_added():
    old = "Party B provides services."
    new = "Party B provides services and shall indemnify Party A against all claims."
    hits = apply_rules(old, new)
    ids = [h.rule_id for h in hits]
    assert "rights.indemnity_added" in ids


# ── Risk score ────────────────────────────────────────────────────────────────

def test_risk_score_proportional():
    old = "Party A shall pay $10,000 within 30 days."
    new = "Party A may pay $100,000 within 90 days. All disputes go to arbitration. Party A waives liability claims."
    hits = apply_rules(old, new)
    score = rule_risk_score(hits)
    assert score >= 60  # multiple critical/high hits


def test_risk_score_zero_for_identical():
    text = "The parties agree to collaborate."
    hits = apply_rules(text, text)
    score = rule_risk_score(hits)
    assert score == 0


def test_risk_score_capped_at_100():
    old = "Simple clause."
    new = ("Party A waives all rights. No liability. Arbitration required. "
           "Irrevocable perpetual license. Penalty of $1,000,000. "
           "Shall replaced by may. Indemnification added.")
    hits = apply_rules(old, new)
    score = rule_risk_score(hits)
    assert score <= 100
