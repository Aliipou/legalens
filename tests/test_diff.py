"""Tests for the semantic diff engine."""
import pytest

from app.diff.engine import diff_documents, ChangeType, _split_clauses


def test_split_clauses_basic():
    text = "First clause here.\n\nSecond clause here.\n\nThird clause here."
    clauses = _split_clauses(text)
    assert len(clauses) == 3
    assert clauses[0].text == "First clause here."


def test_split_clauses_empty():
    assert _split_clauses("") == []
    assert _split_clauses("   \n\n  ") == []


def test_diff_identical_documents():
    doc = "This agreement is entered into between Party A and Party B.\n\nBoth parties agree to the terms."
    result = diff_documents(doc, doc)
    assert result.overall_risk == "low"
    modified_or_added = [d for d in result.diffs if d.change_type in (ChangeType.ADDED, ChangeType.REMOVED)]
    assert len(modified_or_added) == 0


def test_diff_added_clause():
    old = "Party A agrees to pay Party B.\n\nThis contract is governed by Finnish law."
    new = "Party A agrees to pay Party B.\n\nThis contract is governed by Finnish law.\n\nParty A waives all rights to indemnification."
    result = diff_documents(old, new)
    assert any(d.change_type == ChangeType.ADDED for d in result.diffs)
    assert result.total_clauses_new > result.total_clauses_old


def test_diff_removed_clause():
    old = "Party A agrees to pay Party B.\n\nParty B provides unlimited liability coverage.\n\nGoverned by Finnish law."
    new = "Party A agrees to pay Party B.\n\nGoverned by Finnish law."
    result = diff_documents(old, new)
    assert any(d.change_type == ChangeType.REMOVED for d in result.diffs)


def test_diff_counts_summary():
    old = "Section 1: Payment terms.\n\nSection 2: Termination clause.\n\nSection 3: Governing law."
    new = "Section 1: Payment terms revised.\n\nSection 3: Governing law.\n\nSection 4: New arbitration clause."
    result = diff_documents(old, new)
    assert result.summary != ""
    assert "added" in result.summary.lower()


def test_diff_overall_risk_levels():
    low_old = "The parties agree to collaborate."
    low_new = "The parties agree to collaborate on this project."
    result = diff_documents(low_old, low_new)
    assert result.overall_risk in ("low", "medium", "high")
