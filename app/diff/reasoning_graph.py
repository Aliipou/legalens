"""Reasoning graph: causal DAG from text observation through rule hits to risk conclusion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GraphNode:
    id: str
    type: str   # observation | rule_hit | signal | score | conclusion
    label: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    label: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def build(
    clause_id: str,
    old_text: str | None,
    new_text: str | None,
    similarity: float | None,
    rule_hits: list,          # list[RuleHit]
    semantic_score: float,
    rule_score: int,
    structural_score: int,
    combined: float,
    level: str,
    calibration_probs: dict[str, float],
) -> ReasoningGraph:
    # Weights are retrieved from calibration metadata for transparency.
    # We expose the model's effective contribution per signal in the graph.
    from app.diff.calibration import _calibrator
    import numpy as np

    cal = _calibrator()
    x = (np.array([semantic_score, rule_score, structural_score], dtype=float) - cal._mean) / cal._scale
    logits = cal._coef @ x + cal._intercept
    e = np.exp(logits - logits.max())
    probs = e / e.sum()
    # Effective contribution: gradient of log-odds for the predicted class
    pred_class = int(probs.argmax())
    coef_row = cal._coef[pred_class]
    coef_scaled = coef_row / cal._scale
    total_abs = float(abs(coef_scaled).sum()) or 1.0
    eff_weights = {
        "semantic": round(float(abs(coef_scaled[0])) / total_abs, 3),
        "rule": round(float(abs(coef_scaled[1])) / total_abs, 3),
        "structural": round(float(abs(coef_scaled[2])) / total_abs, 3),
    }

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    cid = clause_id.replace(".", "_")

    # ── Observation ──────────────────────────────────────────────────────────
    obs_id = f"obs:{cid}"
    nodes.append(GraphNode(
        id=obs_id,
        type="observation",
        label=f"Text change detected in clause {clause_id}",
        data={
            "old_excerpt": (old_text or "")[:120].strip(),
            "new_excerpt": (new_text or "")[:120].strip(),
            "similarity": similarity,
        },
    ))

    # ── Rule hit nodes ───────────────────────────────────────────────────────
    rule_agg_id = f"sig:rule:{cid}"
    nodes.append(GraphNode(
        id=rule_agg_id,
        type="signal",
        label=f"Rule score: {rule_score}/100",
        data={"value": rule_score, "effective_weight": eff_weights["rule"]},
    ))
    edges.append(GraphEdge(obs_id, rule_agg_id, "produces"))

    for hit in rule_hits:
        hit_node_id = f"hit:{hit.rule_id.replace('.', '_')}:{cid}"
        nodes.append(GraphNode(
            id=hit_node_id,
            type="rule_hit",
            label=hit.description,
            data={
                "rule_id": hit.rule_id,
                "severity": hit.severity.value,
                "old_snippet": hit.old_snippet,
                "new_snippet": hit.new_snippet,
            },
        ))
        edges.append(GraphEdge(obs_id, hit_node_id, "triggers"))
        edges.append(GraphEdge(
            hit_node_id, rule_agg_id, "contributes",
            {"severity": hit.severity.value},
        ))

    # ── Semantic signal ──────────────────────────────────────────────────────
    sem_id = f"sig:semantic:{cid}"
    nodes.append(GraphNode(
        id=sem_id,
        type="signal",
        label=f"Semantic distance: {semantic_score:.1f}/100",
        data={"value": semantic_score, "similarity": similarity, "effective_weight": eff_weights["semantic"]},
    ))
    edges.append(GraphEdge(obs_id, sem_id, "produces"))

    # ── Structural signal ────────────────────────────────────────────────────
    struct_id = f"sig:structural:{cid}"
    nodes.append(GraphNode(
        id=struct_id,
        type="signal",
        label=f"Structural importance: {structural_score}/100",
        data={"value": structural_score, "effective_weight": eff_weights["structural"]},
    ))

    # ── Combined score ───────────────────────────────────────────────────────
    score_id = f"score:{cid}"
    nodes.append(GraphNode(
        id=score_id,
        type="score",
        label=f"Calibrated risk score: {combined}",
        data={
            "value": combined,
            "calibration_probs": calibration_probs,
            "effective_weights": eff_weights,
        },
    ))
    edges.append(GraphEdge(sem_id, score_id, "weighted_input", {"effective_weight": eff_weights["semantic"]}))
    edges.append(GraphEdge(rule_agg_id, score_id, "weighted_input", {"effective_weight": eff_weights["rule"]}))
    edges.append(GraphEdge(struct_id, score_id, "weighted_input", {"effective_weight": eff_weights["structural"]}))

    # ── Conclusion ───────────────────────────────────────────────────────────
    conc_id = f"conclusion:{cid}"
    nodes.append(GraphNode(
        id=conc_id,
        type="conclusion",
        label=f"Risk level: {level.upper()}",
        data={"level": level, "calibration_probs": calibration_probs},
    ))
    edges.append(GraphEdge(score_id, conc_id, "determines"))

    return ReasoningGraph(nodes=nodes, edges=edges)
