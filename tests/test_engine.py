"""Integration tests for the full diff engine pipeline."""
from app.diff.engine import ChangeType, diff_documents


def test_identical_documents_no_changes():
    doc = """1. Payment Terms
Party A shall pay within 30 days.

2. Governing Law
This agreement is governed by Finnish law."""
    result = diff_documents(doc, doc)
    modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
    assert len(modified) == 0
    assert result.overall_risk == "low"


def test_added_clause_detected():
    old = "1. Payment\nParty A shall pay within 30 days."
    new = ("1. Payment\nParty A shall pay within 30 days.\n\n"
           "2. Arbitration\nAll disputes shall go to binding arbitration.")
    result = diff_documents(old, new)
    assert result.total_clauses_new > result.total_clauses_old
    assert len(result.added) >= 1


def test_removed_clause_flagged_high_risk():
    old = ("1. Payment\nParty A shall pay within 30 days.\n\n"
           "2. Limitation of Liability\nCompany shall not be liable for indirect damages.")
    new = "1. Payment\nParty A shall pay within 30 days."
    result = diff_documents(old, new)
    assert len(result.removed) >= 1
    removed = result.removed[0]
    assert removed.risk.level in ("high", "critical")


def test_shall_to_may_raises_overall_risk():
    old = "1. Delivery\nParty B shall deliver goods within 30 days of order."
    new = "1. Delivery\nParty B may deliver goods within 30 days of order."
    result = diff_documents(old, new)
    assert result.overall_risk in ("high", "critical", "medium")
    modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
    if modified:
        rule_ids = [h.rule_id for d in modified for h in d.rule_hits]
        assert "obligation.shall_to_may" in rule_ids


def test_penalty_addition_detected():
    old = "1. Payment\nFees are due monthly."
    new = "1. Payment\nFees are due monthly. Late payment incurs a 5% penalty per month."
    result = diff_documents(old, new)
    modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
    all_rule_ids = [h.rule_id for d in modified for h in d.rule_hits]
    assert any("penalty" in rid for rid in all_rule_ids)


def test_deadline_change_in_response():
    old = "1. Notice\nParty must give 30 days notice of termination."
    new = "1. Notice\nParty must give 90 days notice of termination."
    result = diff_documents(old, new)
    modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
    all_rule_ids = [h.rule_id for d in modified for h in d.rule_hits]
    assert "deadline.changed" in all_rule_ids


def test_result_has_drivers():
    old = "1. Scope\nCompany provides services globally."
    new = "1. Scope\nCompany provides irrevocable, perpetual services globally with no liability."
    result = diff_documents(old, new)
    modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
    assert any(len(d.risk.drivers) > 0 for d in modified)


def test_empty_documents():
    result = diff_documents("", "")
    assert result.total_clauses_old == 0
    assert result.total_clauses_new == 0
    assert result.overall_risk == "low"


def test_summary_contains_risk_level():
    old = "1. Obligations\nParty A shall perform."
    new = "1. Obligations\nParty A may perform. No liability applies."
    result = diff_documents(old, new)
    assert result.overall_risk in result.summary.lower() or "risk" in result.summary.lower()


def test_combined_risk_score_range():
    old = "1. Payment\nParty A shall pay $1,000 within 30 days."
    new = "1. Payment\nParty A may pay $100,000 within 180 days. Late payment incurs arbitration."
    result = diff_documents(old, new)
    for d in result.diffs:
        assert 0 <= d.risk.combined <= 100
        assert d.risk.level in ("low", "medium", "high", "critical")


def test_hierarchical_lettered_subclauses():
    old = """2. Obligations
Party A agrees to:
(a) deliver within 30 days
(b) maintain quality standards"""
    new = """2. Obligations
Party A agrees to:
(a) deliver within 90 days
(b) maintain quality standards
(c) pay a penalty of $10,000 for breach"""
    result = diff_documents(old, new)
    assert result.total_clauses_new >= result.total_clauses_old
