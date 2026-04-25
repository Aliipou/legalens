"""Tests for the reasoning graph builder."""
from app.diff.rule_engine import RuleHit, RuleSeverity
from app.diff.reasoning_graph import ReasoningGraph, build


def _make_graph(rule_hits=None, similarity=0.72):
    return build(
        clause_id="1.2",
        old_text="Party A shall pay within 30 days.",
        new_text="Party A may pay within 90 days.",
        similarity=similarity,
        rule_hits=rule_hits or [],
        semantic_score=28.0,
        rule_score=55,
        structural_score=40,
        combined=52.3,
        level="high",
        calibration_probs={"low": 0.05, "medium": 0.1, "high": 0.65, "critical": 0.2},
    )


def test_graph_is_reasoning_graph():
    g = _make_graph()
    assert isinstance(g, ReasoningGraph)


def test_graph_has_nodes_and_edges():
    g = _make_graph()
    assert len(g.nodes) >= 5
    assert len(g.edges) >= 4


def test_observation_node_present():
    g = _make_graph()
    obs = [n for n in g.nodes if n.type == "observation"]
    assert len(obs) == 1
    assert "1.2" in obs[0].label


def test_conclusion_node_present():
    g = _make_graph()
    conc = [n for n in g.nodes if n.type == "conclusion"]
    assert len(conc) == 1
    assert "HIGH" in conc[0].label


def test_rule_hit_nodes_added():
    hits = [
        RuleHit("obligation.shall_to_may", RuleSeverity.CRITICAL, "Obligation weakened.", "shall", "may"),
        RuleHit("deadline.changed", RuleSeverity.HIGH, "Deadline extended.", "30 days", "90 days"),
    ]
    g = _make_graph(rule_hits=hits)
    hit_nodes = [n for n in g.nodes if n.type == "rule_hit"]
    assert len(hit_nodes) == 2
    rule_ids = [n.data["rule_id"] for n in hit_nodes]
    assert "obligation.shall_to_may" in rule_ids
    assert "deadline.changed" in rule_ids


def test_all_signals_present():
    g = _make_graph()
    signals = [n for n in g.nodes if n.type == "signal"]
    assert len(signals) >= 2  # rule_agg + semantic (structural in nodes too)


def test_score_node_has_calibration_probs():
    g = _make_graph()
    score_nodes = [n for n in g.nodes if n.type == "score"]
    assert len(score_nodes) == 1
    assert "calibration_probs" in score_nodes[0].data


def test_effective_weights_sum_approx_one():
    g = _make_graph()
    score_node = next(n for n in g.nodes if n.type == "score")
    weights = score_node.data["effective_weights"]
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01


def test_edges_reference_existing_nodes():
    g = _make_graph()
    node_ids = {n.id for n in g.nodes}
    for e in g.edges:
        assert e.source in node_ids, f"Edge source {e.source!r} not in nodes"
        assert e.target in node_ids, f"Edge target {e.target!r} not in nodes"


def test_no_dangling_nodes():
    g = _make_graph()
    referenced = {e.source for e in g.edges} | {e.target for e in g.edges}
    node_ids = {n.id for n in g.nodes}
    # Every non-root node must appear in at least one edge
    # (root = observation node, which has no incoming edge)
    for nid in node_ids:
        n = next(nn for nn in g.nodes if nn.id == nid)
        if n.type != "observation":
            assert nid in referenced, f"Node {nid!r} is dangling"


def test_graph_with_no_rule_hits():
    g = _make_graph(rule_hits=[])
    assert len(g.nodes) >= 5
    conc = next(n for n in g.nodes if n.type == "conclusion")
    assert conc.data["level"] == "high"
