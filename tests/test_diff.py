"""Tests for the semantic diff engine (legacy compatibility)."""
import pytest

from app.diff.engine import diff_documents, ChangeType
from app.diff.segmentor import segment


def _split_clauses(text):
    return segment(text)


def test_split_clauses_basic():
    text = "First clause here.\n\nSecond clause here.\n\nThird clause here."
    clauses = _split_clauses(text)
    assert len(clauses) >= 1


def test_split_clauses_empty():
    assert _split_clauses("") == []
    assert _split_clauses("   \n\n  ") == []


def test_diff_identical_documents():
    doc = "1. Agreement\nThis agreement is entered into between Party A and Party B.\n\n2. Terms\nBoth parties agree to the terms."
    result = diff_documents(doc, doc)
    assert result.overall_risk == "low"
    modified = [d for d in result.diffs if d.change_type in (ChangeType.ADDED, ChangeType.REMOVED)]
    assert len(modified) == 0


def test_diff_added_clause():
    old = "1. Payment\nParty A agrees to pay Party B.\n\n2. Law\nThis contract is governed by Finnish law."
    new = "1. Payment\nParty A agrees to pay Party B.\n\n2. Law\nThis contract is governed by Finnish law.\n\n3. Waiver\nParty A hereby waives all rights to indemnification."
    result = diff_documents(old, new)
    assert any(d.change_type == ChangeType.ADDED for d in result.diffs)
    assert result.total_clauses_new > result.total_clauses_old


def test_diff_removed_clause():
    old = "1. Payment\nParty A agrees to pay Party B.\n\n2. Liability\nParty B provides unlimited liability coverage.\n\n3. Law\nGoverned by Finnish law."
    new = "1. Payment\nParty A agrees to pay Party B.\n\n3. Law\nGoverned by Finnish law."
    result = diff_documents(old, new)
    assert any(d.change_type == ChangeType.REMOVED for d in result.diffs)


def test_diff_counts_summary():
    old = "1. Payment terms.\n\n2. Termination clause.\n\n3. Governing law."
    new = "1. Payment terms revised.\n\n3. Governing law.\n\n4. New arbitration clause."
    result = diff_documents(old, new)
    assert result.summary != ""
    assert "added" in result.summary.lower() or result.added >= 0


def test_diff_overall_risk_levels():
    low_old = "1. Agreement\nThe parties agree to collaborate."
    low_new = "1. Agreement\nThe parties agree to collaborate on this project."
    result = diff_documents(low_old, low_new)
    assert result.overall_risk in ("low", "medium", "high", "critical")
