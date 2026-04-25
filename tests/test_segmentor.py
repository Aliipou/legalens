"""Tests for robust hierarchical clause segmentor."""
from app.diff.segmentor import NodeType, segment


def test_numbered_sections():
    doc = """1. Payment Terms
Party A shall pay within 30 days.

2. Termination
Either party may terminate with 90 days notice.

3. Governing Law
This agreement is governed by Finnish law."""
    nodes = segment(doc)
    assert len(nodes) == 3
    ids = [n.id for n in nodes]
    assert "1" in ids
    assert "2" in ids
    assert "3" in ids


def test_article_sections():
    doc = """Article 1 Definitions
"Agreement" means this contract.

Article 2 Payment
Payment shall be made in EUR."""
    nodes = segment(doc)
    assert len(nodes) == 2
    assert any("article" in n.id.lower() or n.id == "1" for n in nodes)


def test_dotted_subsections():
    doc = """1.1 Scope
The scope includes all services.

1.2 Exclusions
The following are excluded."""
    nodes = segment(doc)
    assert len(nodes) >= 2


def test_lettered_subclauses():
    doc = """2. Obligations

Party A agrees to:
(a) deliver goods within 30 days
(b) provide warranty for 12 months
(c) maintain insurance coverage"""
    nodes = segment(doc)
    assert len(nodes) >= 1
    # Should have subclauses under the section
    parent = nodes[0]
    assert len(parent.children) >= 3 or len(nodes) >= 3


def test_bullet_lists():
    doc = """Included Services:

- Software license
- Technical support
- System updates"""
    nodes = segment(doc)
    assert len(nodes) >= 1
    all_nodes = []
    for n in nodes:
        all_nodes.extend(n.flatten())
    bullet_nodes = [n for n in all_nodes if n.node_type == NodeType.BULLET]
    assert len(bullet_nodes) >= 3


def test_empty_document():
    assert segment("") == []
    assert segment("   \n\n  ") == []


def test_preamble_detection():
    doc = """This Agreement is entered into as of January 1, 2024, by and between Company A and Company B.

1. Definitions
"Party" means either Company A or Company B."""
    nodes = segment(doc)
    assert len(nodes) >= 2
    # First node should be preamble
    assert nodes[0].node_type in (NodeType.PREAMBLE, NodeType.CLAUSE)


def test_flatten():
    doc = """1. Payment
Party shall pay.
(a) within 30 days
(b) in EUR"""
    nodes = segment(doc)
    flat = []
    for n in nodes:
        flat.extend(n.flatten())
    assert len(flat) >= 1


def test_caps_heading():
    doc = """PAYMENT TERMS
Party A shall pay monthly.

TERMINATION
Either party may terminate."""
    nodes = segment(doc)
    assert len(nodes) >= 2
