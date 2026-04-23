"""Semantic + structural diff engine for legal documents."""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class Clause:
    index: int
    text: str
    heading: str | None = None


@dataclass
class ClauseDiff:
    change_type: ChangeType
    old_clause: Clause | None
    new_clause: Clause | None
    similarity: float | None = None
    semantic_risk: str = "low"
    key_changes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            txt = (self.new_clause.text[:100] if self.new_clause else "")
            return f"New clause added: \"{txt}...\""
        if self.change_type == ChangeType.REMOVED:
            txt = (self.old_clause.text[:100] if self.old_clause else "")
            return f"Clause removed: \"{txt}...\""
        if self.change_type == ChangeType.MODIFIED:
            return f"Clause modified (similarity={self.similarity:.2f}): risk={self.semantic_risk}"
        return "Unchanged"


@dataclass
class DiffResult:
    total_clauses_old: int
    total_clauses_new: int
    diffs: list[ClauseDiff]
    overall_risk: str
    summary: str

    @property
    def added(self) -> list[ClauseDiff]:
        return [d for d in self.diffs if d.change_type == ChangeType.ADDED]

    @property
    def removed(self) -> list[ClauseDiff]:
        return [d for d in self.diffs if d.change_type == ChangeType.REMOVED]

    @property
    def modified(self) -> list[ClauseDiff]:
        return [d for d in self.diffs if d.change_type == ChangeType.MODIFIED]


_HEADING_RE = re.compile(r"^(#{1,6}\s+.+|[A-Z][A-Z\s]{4,}|(?:\d+\.)+\s+[A-Z].{3,})", re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_clauses(text: str) -> list[Clause]:
    """Split document into logical clauses (paragraphs or numbered items)."""
    blocks = re.split(r"\n{2,}", text.strip())
    clauses: list[Clause] = []
    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue
        heading = None
        if _HEADING_RE.match(block):
            heading = block.splitlines()[0]
        clauses.append(Clause(index=i, text=block, heading=heading))
    return clauses


@lru_cache(maxsize=1)
def _load_model(model_name: str) -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def _embed(texts: list[str], model_name: str) -> np.ndarray:
    model = _load_model(model_name)
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _risk_from_similarity(sim: float) -> str:
    if sim >= 0.95:
        return "low"
    if sim >= 0.80:
        return "medium"
    return "high"


_RISKY_TERMS = re.compile(
    r"\b(indemnif|liabilit|terminat|arbitrat|exclusive|waiv|forfeit|penalt|liquidat|warrant|irrevoc|perpetual)\w*",
    re.IGNORECASE,
)


def _extract_key_changes(old_text: str, new_text: str) -> list[str]:
    old_words = set(old_text.lower().split())
    new_words = set(new_text.lower().split())
    added_words = new_words - old_words
    removed_words = old_words - new_words
    changes = []
    for w in sorted(added_words):
        if _RISKY_TERMS.search(w):
            changes.append(f"+{w}")
    for w in sorted(removed_words):
        if _RISKY_TERMS.search(w):
            changes.append(f"-{w}")
    return changes[:10]


def diff_documents(
    old_text: str,
    new_text: str,
    model_name: str = "all-MiniLM-L6-v2",
    similarity_threshold: float = 0.85,
) -> DiffResult:
    old_clauses = _split_clauses(old_text)
    new_clauses = _split_clauses(new_text)

    if not old_clauses and not new_clauses:
        return DiffResult(0, 0, [], "low", "Both documents are empty.")

    all_texts = [c.text for c in old_clauses] + [c.text for c in new_clauses]
    embeddings = _embed(all_texts, model_name)
    old_embs = embeddings[: len(old_clauses)]
    new_embs = embeddings[len(old_clauses) :]

    # Greedy matching: pair each old clause to the best new clause above threshold
    matched_new: set[int] = set()
    matched_old: set[int] = set()
    pairs: list[tuple[int, int, float]] = []

    if len(old_clauses) > 0 and len(new_clauses) > 0:
        sim_matrix = old_embs @ new_embs.T  # (n_old, n_new)
        for oi in range(len(old_clauses)):
            best_ni = int(np.argmax(sim_matrix[oi]))
            best_sim = float(sim_matrix[oi, best_ni])
            if best_sim >= similarity_threshold and best_ni not in matched_new:
                pairs.append((oi, best_ni, best_sim))
                matched_new.add(best_ni)
                matched_old.add(oi)

    diffs: list[ClauseDiff] = []

    for oi, ni, sim in pairs:
        old_c = old_clauses[oi]
        new_c = new_clauses[ni]
        if old_c.text == new_c.text:
            diffs.append(ClauseDiff(ChangeType.UNCHANGED, old_c, new_c, sim))
        else:
            key_changes = _extract_key_changes(old_c.text, new_c.text)
            risk = _risk_from_similarity(sim)
            diffs.append(ClauseDiff(ChangeType.MODIFIED, old_c, new_c, sim, risk, key_changes))

    for oi, c in enumerate(old_clauses):
        if oi not in matched_old:
            diffs.append(ClauseDiff(ChangeType.REMOVED, c, None, None, "high"))

    for ni, c in enumerate(new_clauses):
        if ni not in matched_new:
            diffs.append(ClauseDiff(ChangeType.ADDED, None, c, None, "medium"))

    high_count = sum(1 for d in diffs if d.semantic_risk == "high")
    med_count = sum(1 for d in diffs if d.semantic_risk == "medium")
    if high_count >= 3 or (high_count >= 1 and med_count >= 3):
        overall_risk = "high"
    elif high_count >= 1 or med_count >= 2:
        overall_risk = "medium"
    else:
        overall_risk = "low"

    n_added = sum(1 for d in diffs if d.change_type == ChangeType.ADDED)
    n_removed = sum(1 for d in diffs if d.change_type == ChangeType.REMOVED)
    n_modified = sum(1 for d in diffs if d.change_type == ChangeType.MODIFIED)
    summary = (
        f"{n_added} clause(s) added, {n_removed} removed, {n_modified} modified. "
        f"Overall risk: {overall_risk}."
    )

    return DiffResult(
        total_clauses_old=len(old_clauses),
        total_clauses_new=len(new_clauses),
        diffs=diffs,
        overall_risk=overall_risk,
        summary=summary,
    )
