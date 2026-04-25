"""Robust legal document clause segmentor with hierarchical structure."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class NodeType(str, Enum):
    DOCUMENT = "document"
    SECTION = "section"
    CLAUSE = "clause"
    SUBCLAUSE = "subclause"
    BULLET = "bullet"
    PREAMBLE = "preamble"


@dataclass
class ClauseNode:
    id: str                          # e.g. "1", "1.1", "1.1.a", "preamble"
    node_type: NodeType
    heading: str | None
    text: str
    depth: int
    children: list["ClauseNode"] = field(default_factory=list)
    parent_id: str | None = None

    @property
    def full_text(self) -> str:
        """Full text including all children."""
        parts = [self.text]
        for child in self.children:
            parts.append(child.full_text)
        return "\n".join(p for p in parts if p)

    def flatten(self) -> list["ClauseNode"]:
        """Return this node and all descendants as a flat list."""
        result = [self]
        for child in self.children:
            result.extend(child.flatten())
        return result


# ── Pattern library ──────────────────────────────────────────────────────────

# Numbered section: "1.", "1.1", "1.1.2", "Article 1", "Section 2", "ARTICLE I"
_SECTION_NUM = re.compile(
    r"^(?:"
    r"(?:Article|Section|ARTICLE|SECTION)\s+[\dIVXivx]+[a-z]?\b"
    r"|(?:\d+\.)+\d*\s"
    r"|\d+\.\s"
    r")",
    re.MULTILINE,
)

# Lettered subclause: "(a)", "(b)", "(i)", "(ii)"
_LETTERED = re.compile(r"^\s*\(([a-z]|[ivx]+)\)\s+", re.MULTILINE)

# Bullet: "•", "-", "*", "–" at start of line
_BULLET = re.compile(r"^\s*[•\-\*–]\s+", re.MULTILINE)

# ALL-CAPS heading (≥3 words or ≥ 8 chars): "PAYMENT TERMS", "GOVERNING LAW"
_CAPS_HEADING = re.compile(r"^([A-Z][A-Z\s]{7,})$", re.MULTILINE)

# Extract section number prefix
_SECTION_ID = re.compile(
    r"^(?:(Article|Section|ARTICLE|SECTION)\s+([\dIVXivx]+[a-z]?)"
    r"|((?:\d+\.)+\d*)\s"
    r"|(\d+)\.\s)",
    re.MULTILINE,
)


def _extract_section_id(line: str) -> str | None:
    m = _SECTION_ID.match(line.strip())
    if not m:
        return None
    if m.group(1):
        return f"{m.group(1).lower()}-{m.group(2)}"
    if m.group(3):
        return m.group(3).rstrip(".")
    if m.group(4):
        return m.group(4)
    return None


def _split_top_level(text: str) -> list[tuple[str | None, str]]:
    """Split document into top-level blocks preserving section IDs."""
    lines = text.split("\n")
    blocks: list[tuple[str | None, str]] = []
    current_id: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue

        sid = _extract_section_id(stripped)
        caps = bool(_CAPS_HEADING.match(stripped)) and len(stripped) < 80

        if sid or caps:
            if current_lines:
                blocks.append((current_id, "\n".join(current_lines).strip()))
                current_lines = []
            current_id = sid or stripped[:40]
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        blocks.append((current_id, "\n".join(current_lines).strip()))

    return [(sid, txt) for sid, txt in blocks if txt.strip()]


def _parse_subclauses(text: str, parent_id: str, depth: int) -> list[ClauseNode]:
    """Parse (a)/(b) lettered subclauses or bullets within a clause body."""
    nodes: list[ClauseNode] = []

    # Try lettered subclauses
    parts = re.split(r"(\n\s*\([a-z]\)\s+|\n\s*\([ivx]+\)\s+)", text)
    if len(parts) > 1:
        # first part is preamble
        preamble = parts[0].strip()
        i = 1
        while i < len(parts) - 1:
            label = parts[i].strip().strip("()")
            body = parts[i + 1].strip()
            node_id = f"{parent_id}.{label}"
            nodes.append(ClauseNode(
                id=node_id,
                node_type=NodeType.SUBCLAUSE,
                heading=f"({label})",
                text=body,
                depth=depth + 1,
                parent_id=parent_id,
            ))
            i += 2
        return nodes, preamble

    # Try bullet lists
    bullets = re.split(r"\n\s*[•\-\*–]\s+", text)
    if len(bullets) > 2:
        preamble = bullets[0].strip()
        for j, b in enumerate(bullets[1:], 1):
            b = b.strip()
            if b:
                nodes.append(ClauseNode(
                    id=f"{parent_id}.bullet{j}",
                    node_type=NodeType.BULLET,
                    heading=None,
                    text=b,
                    depth=depth + 1,
                    parent_id=parent_id,
                ))
        return nodes, preamble

    return [], text


def segment(text: str) -> list[ClauseNode]:
    """Segment a legal document into a flat list of hierarchical ClauseNodes."""
    if not text.strip():
        return []

    top_blocks = _split_top_level(text)
    nodes: list[ClauseNode] = []
    counter = 0

    for raw_id, block_text in top_blocks:
        counter += 1
        node_id = raw_id or str(counter)

        # Detect heading on first line
        first_line = block_text.splitlines()[0].strip()
        rest = "\n".join(block_text.splitlines()[1:]).strip()

        is_heading_line = bool(
            _SECTION_NUM.match(first_line)
            or _CAPS_HEADING.match(first_line)
            or _LETTERED.match(first_line)
        )
        heading = first_line if is_heading_line else None
        body = rest if is_heading_line else block_text

        children, body_clean = _parse_subclauses(body, node_id, depth=1)

        node_type = NodeType.SECTION if (heading or raw_id) else NodeType.CLAUSE
        if counter == 1 and not heading and not raw_id:
            node_type = NodeType.PREAMBLE

        parent_node = ClauseNode(
            id=node_id,
            node_type=node_type,
            heading=heading,
            text=body_clean,
            depth=0,
            children=children,
        )
        nodes.append(parent_node)

    return nodes
