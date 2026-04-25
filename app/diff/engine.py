"""Orchestrator: segment → match → rule engine → hybrid risk score → result."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.diff.matcher import ClauseMatch, match_clauses
from app.diff.reasoning_graph import ReasoningGraph
from app.diff.reasoning_graph import build as build_graph
from app.diff.risk_scorer import RiskScore
from app.diff.risk_scorer import compute as compute_risk
from app.diff.rule_engine import RuleHit, apply_rules
from app.diff.segmentor import ClauseNode, segment


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class ClauseDiff:
    change_type: ChangeType
    old_clause: ClauseNode | None
    new_clause: ClauseNode | None
    match_type: str
    similarity: float | None
    rule_hits: list[RuleHit]
    risk: RiskScore
    reasoning_graph: ReasoningGraph | None = None

    @property
    def semantic_risk(self) -> str:
        return self.risk.level

    @property
    def key_changes(self) -> list[str]:
        return self.risk.drivers

    @property
    def summary(self) -> str:
        if self.change_type == ChangeType.ADDED:
            txt = self.new_clause.text[:100] if self.new_clause else ""
            return f"Clause added: \"{txt}...\""
        if self.change_type == ChangeType.REMOVED:
            txt = self.old_clause.text[:100] if self.old_clause else ""
            return f"Clause removed: \"{txt}...\""
        if self.change_type == ChangeType.MODIFIED:
            rule_count = len(self.rule_hits)
            r = f", {rule_count} rule hit(s)" if rule_count else ""
            return f"Modified (similarity={self.similarity:.2f}{r}): risk={self.risk.level}"
        return "Unchanged"


@dataclass
class DiffResult:
    total_clauses_old: int
    total_clauses_new: int
    diffs: list[ClauseDiff]
    overall_risk: str
    summary: str
    document_structure_old: list[ClauseNode] = field(default_factory=list)
    document_structure_new: list[ClauseNode] = field(default_factory=list)

    @property
    def added(self) -> list[ClauseDiff]:
        return [d for d in self.diffs if d.change_type == ChangeType.ADDED]

    @property
    def removed(self) -> list[ClauseDiff]:
        return [d for d in self.diffs if d.change_type == ChangeType.REMOVED]

    @property
    def modified(self) -> list[ClauseDiff]:
        return [d for d in self.diffs if d.change_type == ChangeType.MODIFIED]


def diff_documents(
    old_text: str,
    new_text: str,
    model_name: str = "all-MiniLM-L6-v2",
    similarity_threshold: float = 0.85,
) -> DiffResult:
    # 1. Segment into hierarchical clause trees
    old_tree = segment(old_text)
    new_tree = segment(new_text)

    # 2. Flatten to leaf+section nodes for matching
    old_flat = _flatten(old_tree)
    new_flat = _flatten(new_tree)

    if not old_flat and not new_flat:
        return DiffResult(0, 0, [], "low", "Both documents are empty.",
                          old_tree, new_tree)

    # 3. Match clauses: ID-first → semantic fallback
    clause_matches = match_clauses(old_flat, new_flat, model_name, similarity_threshold)

    # 4. Build ClauseDiff for each match
    diffs: list[ClauseDiff] = []
    for m in clause_matches:
        diffs.append(_build_diff(m))

    # 5. Compute overall risk
    overall_risk = _overall_risk(diffs)

    n_added = len([d for d in diffs if d.change_type == ChangeType.ADDED])
    n_removed = len([d for d in diffs if d.change_type == ChangeType.REMOVED])
    n_modified = len([d for d in diffs if d.change_type == ChangeType.MODIFIED])
    critical = sum(1 for d in diffs if d.risk.level == "critical")
    high = sum(1 for d in diffs if d.risk.level == "high")

    summary_parts = [
        f"{n_added} added, {n_removed} removed, {n_modified} modified.",
        f"Overall risk: {overall_risk}.",
    ]
    if critical:
        summary_parts.append(f"{critical} critical change(s).")
    if high:
        summary_parts.append(f"{high} high-risk change(s).")

    return DiffResult(
        total_clauses_old=len(old_flat),
        total_clauses_new=len(new_flat),
        diffs=diffs,
        overall_risk=overall_risk,
        summary=" ".join(summary_parts),
        document_structure_old=old_tree,
        document_structure_new=new_tree,
    )


def _flatten(tree: list[ClauseNode]) -> list[ClauseNode]:
    """Return all nodes (sections + leaf clauses) suitable for matching."""
    result = []
    for node in tree:
        result.append(node)
        for child in node.children:
            result.append(child)
    return result


def _build_diff(m: ClauseMatch) -> ClauseDiff:
    if m.old_node is None and m.new_node is not None:
        risk = compute_risk(
            similarity=None,
            rule_hits=[],
            node_type=m.new_node.node_type.value,
            heading=m.new_node.heading,
        )
        # New clause: medium structural risk
        risk.level = "medium"
        return ClauseDiff(
            change_type=ChangeType.ADDED,
            old_clause=None,
            new_clause=m.new_node,
            match_type=m.match_type.value,
            similarity=None,
            rule_hits=[],
            risk=risk,
        )

    if m.new_node is None and m.old_node is not None:
        risk = compute_risk(
            similarity=None,
            rule_hits=[],
            node_type=m.old_node.node_type.value,
            heading=m.old_node.heading,
        )
        risk.level = "high"
        return ClauseDiff(
            change_type=ChangeType.REMOVED,
            old_clause=m.old_node,
            new_clause=None,
            match_type=m.match_type.value,
            similarity=None,
            rule_hits=[],
            risk=risk,
        )

    # Both exist — check if changed
    old_text = m.old_node.text or ""
    new_text = m.new_node.text or ""

    if old_text.strip() == new_text.strip() and m.similarity is not None and m.similarity > 0.999:
        risk = compute_risk(1.0, [], m.old_node.node_type.value, m.old_node.heading)
        return ClauseDiff(
            change_type=ChangeType.UNCHANGED,
            old_clause=m.old_node,
            new_clause=m.new_node,
            match_type=m.match_type.value,
            similarity=m.similarity,
            rule_hits=[],
            risk=risk,
        )

    rule_hits = apply_rules(old_text, new_text)
    risk = compute_risk(
        similarity=m.similarity,
        rule_hits=rule_hits,
        node_type=m.old_node.node_type.value,
        heading=m.old_node.heading,
    )
    graph = build_graph(
        clause_id=m.old_node.id,
        old_text=old_text,
        new_text=new_text,
        similarity=m.similarity,
        rule_hits=rule_hits,
        semantic_score=risk.semantic_score,
        rule_score=risk.rule_score,
        structural_score=risk.structural_score,
        combined=risk.combined,
        level=risk.level,
        calibration_probs=risk.calibration_probs,
    )
    return ClauseDiff(
        change_type=ChangeType.MODIFIED,
        old_clause=m.old_node,
        new_clause=m.new_node,
        match_type=m.match_type.value,
        similarity=m.similarity,
        rule_hits=rule_hits,
        risk=risk,
        reasoning_graph=graph,
    )


def _overall_risk(diffs: list[ClauseDiff]) -> str:
    levels = [d.risk.level for d in diffs if d.change_type != ChangeType.UNCHANGED]
    if not levels:
        return "low"
    if "critical" in levels:
        return "critical"
    high_count = levels.count("high")
    if high_count >= 2:
        return "high"
    if high_count >= 1 or levels.count("medium") >= 3:
        return "medium"
    return "low"
