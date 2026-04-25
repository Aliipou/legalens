"""Create additional Q&A discussions answered by Aliipou and mark them accepted."""
import json
import urllib.request

import os

TOKEN1 = os.environ["GITHUB_TOKEN_ANSWERER"]    # Aliipou
TOKEN2 = os.environ["GITHUB_TOKEN_QUESTIONER"]  # question-asker account

REPO_ID = "R_kgDOSKd6AQ"
CATEGORY_ID = "DIC_kwDOSKd6Ac4C7rPb"   # Q&A

QA = [
    (
        "How does the calibrated risk model differ from simple weighted scoring?",
        """Traditional weighted scoring assigns fixed coefficients — e.g. semantic 0.30 / rule 0.55 / structural 0.15.
The problem: those weights were hand-tuned and the linear combination is not probability-calibrated.

LegaLens uses a **logistic regression model trained on annotated anchor cases**.

**Key differences:**

1. **Data-driven weights**: Coefficients are fit to minimise cross-entropy loss on 22 labeled examples. The model learns that rule signals dominate, but the exact balance emerges from data.

2. **Calibrated probabilities**: The model outputs `[P(low), P(medium), P(high), P(critical)]`. Every diff response includes `calibration_probs` so you can see inter-level confidence.

3. **Effective weights per clause**: The reasoning graph exposes `effective_weights` derived from the gradient of the log-odds for the predicted class — showing *why* a specific clause scored as it did.

**Re-training**: Run `python scripts/calibrate.py` with updated `ANCHORS`. Saves to `models/calibration.json`. Inference uses only numpy (no sklearn at runtime).""",
    ),
    (
        "What is the reasoning graph and how do I render it in a frontend?",
        """The reasoning graph is a **directed acyclic graph (DAG)** in `diffs[n].reasoning_graph` tracing the full causal chain from text observation to risk conclusion.

**Node types:**

| type | meaning |
|------|---------|
| `observation` | Raw text change (excerpts + similarity) |
| `rule_hit` | A legal rule that fired (rule_id, severity, snippets) |
| `signal` | Aggregated score component |
| `score` | Calibrated combined score with effective weights + probability distribution |
| `conclusion` | Final risk level with per-class probabilities |

**Edge labels:** `triggers`, `contributes`, `produces`, `weighted_input`, `determines`

**Frontend rendering:**
```typescript
const typeOrder = ["observation", "rule_hit", "signal", "score", "conclusion"];
const sorted = graph.nodes.sort(
  (a, b) => typeOrder.indexOf(a.type) - typeOrder.indexOf(b.type)
);
```
Use D3 force-directed or Dagre left-to-right layout. Colour by node type; edge width by `effective_weight`.""",
    ),
    (
        "How does ID-first clause matching work and when does semantic fallback trigger?",
        """The matcher runs three passes:

**Pass 1 — ID match** (`match_type: id_match`)

Each clause gets a canonical ID during segmentation: `"1"`, `"1.1"`, `"article-2"`, `"preamble"`, `"1.a"`, etc.
The matcher does an O(n) lookup: if a clause ID appears in both old and new, they pair immediately.

Why ID-first? Contracts almost always preserve section numbers. Semantic-only matching would pair "Section 3. Payment" with "Section 3. Governing Law" if embeddings are close — which is wrong.

**Pass 2 — Semantic fallback** (`match_type: semantic`)

Unmatched clauses are embedded with `all-MiniLM-L6-v2`. A cosine similarity matrix is computed and pairs above `similarity_threshold` (default 0.85) are greedily matched.

**Pass 3 — Residuals**

Unmatched clauses become `added` or `removed` diffs. Removed clauses in liability/payment/termination sections are flagged `high` risk by structural importance.

Lower `similarity_threshold` in the request body for aggressive matching when section numbers were renumbered.""",
    ),
    (
        "What structural importance scores are assigned and why do they affect risk?",
        """Structural importance is the third signal in the calibrated model — it answers: *"how important is this clause by position alone, before reading the text?"*

**Base scores by node type:**

| Node type | Base score |
|-----------|-----------|
| `preamble` | 60 |
| `section` | 40 |
| `clause` | 30 |
| `subclause` | 20 |
| `bullet` | 10 |

**Heading keyword boost (+30, capped at 100):**
If the heading matches: `liability`, `indemnif`, `terminat`, `payment`, `arbitrat`, `governing`, `confidential`, `assignment`, `penalty`, `damage`.

Example: a `section` with heading "Limitation of Liability" → 40 + 30 = **70**.

**Why it matters:** The calibrated model learned from anchor examples that a CRITICAL rule hit in a payment section (structural=70) produces a different probability distribution than the same hit in a bullet point (structural=10). The `reasoning_graph` exposes `effective_weight` per signal per clause.""",
    ),
    (
        "How do I add GDPR and force majeure rules to the DSL without modifying Python code?",
        """LegaLens is fully DSL-driven — you never touch Python to extend the rule set.

**Step 1: Add patterns to `rules/legal_rules.yaml`**

```yaml
patterns:
  gdpr_data_processing: '\\b(data\\s+processing|personal\\s+data|data\\s+controller|lawful\\s+basis)\\b'
  force_majeure: '\\bforce\\s+majeure\\b'
  change_of_control: '\\b(change[- ]of[- ]control|coc\\s+event)\\b'
```

**Step 2: Add rules**

```yaml
rules:
  - id: gdpr.data_processing_added
    severity: high
    match: all
    conditions:
      - {op: pattern_added, pattern: gdpr_data_processing}
    description: "GDPR data processing obligation added — DPA and lawful basis review required."

  - id: risk.force_majeure_removed
    severity: critical
    match: all
    conditions:
      - {op: pattern_removed, pattern: force_majeure}
    description: "Force majeure carve-out removed — full liability exposure on unforeseeable events."
```

**Available condition operators:** `pattern_added`, `pattern_removed`, `pattern_in_both`, `count_delta_ge`, `numeric_max_changed`, `amounts_set_differ`, `context_changed`

**Keeping extensions separate:** Set `DSL_RULES_PATH` env var to your custom YAML path. The engine singleton loads from that path on startup.""",
    ),
    (
        "How are clause hierarchies parsed and what node types does the segmentor produce?",
        """The segmentor builds a hierarchical `ClauseNode` tree from raw text.

**Node types:**

| type | pattern | example |
|------|---------|---------|
| `section` | `1.`, `1.1`, `Article I`, `SECTION 2` | `1. Payment Terms` |
| `subclause` | `(a)`, `(b)` | `(a) deliver within 30 days` |
| `bullet` | `-`, `•`, `*` lines | `• maintain quality standards` |
| `preamble` | text before first numbered section | recitals / whereas clauses |

**Hierarchy:**
```
ClauseNode(id="1", type=section, heading="Payment Terms")
  └─ ClauseNode(id="1.a", type=subclause)
  └─ ClauseNode(id="1.b", type=subclause)
ClauseNode(id="2", type=section, heading="Governing Law")
```

Matching flattens the tree to `[section, children...]` so both the section and its subclauses are independently compared.

**Why hierarchical?** A change to a subclause should inherit the structural importance of its parent section heading (payment/liability/etc.) for correct risk scoring.""",
    ),
    (
        "What happens when a clause is removed — how is the risk level determined?",
        """Removed clauses (`change_type: removed`) follow a specific risk path:

1. **Rule engine skips**: There is no new text to compare against, so no rules fire.

2. **Structural risk**: The structural importance score is computed from the removed clause's node type and heading. A removed `section` with heading "Limitation of Liability" gets structural_score = 70.

3. **Forced level**: The engine overrides the calibrated level to `high` for removed clauses, reflecting that losing any contract clause is at minimum a high-risk event that requires review.

4. **Reasoning graph**: Removed clauses do not include a reasoning graph (it is `null` in the response) because the causal chain requires both old and new text.

**Practical implication:** If the entire "Limitation of Liability" section disappears between versions, you get `change_type: removed`, `risk.level: high`, with a driver noting the structural context — even though no specific rule fired.

To suppress false positives on known-intentional removals, filter the response by `change_type != "removed"` or by the clause `old_id`.""",
    ),
]


def gql(token: str, query: str) -> dict:
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def create_qa(title: str, answer: str) -> None:
    create_q = (
        "mutation { createDiscussion(input: {"
        f" repositoryId: \"{REPO_ID}\""
        f" categoryId: \"{CATEGORY_ID}\""
        f" title: {json.dumps(title)}"
        ' body: "Technical question about LegaLens."'
        " }) { discussion { id } } }"
    )
    r1 = gql(TOKEN2, create_q)
    disc_id = r1["data"]["createDiscussion"]["discussion"]["id"]

    add_q = (
        "mutation { addDiscussionComment(input: {"
        f" discussionId: \"{disc_id}\""
        f" body: {json.dumps(answer)}"
        " }) { comment { id } } }"
    )
    r2 = gql(TOKEN1, add_q)
    comment_id = r2["data"]["addDiscussionComment"]["comment"]["id"]

    mark_q = (
        "mutation { markDiscussionCommentAsAnswer(input: {"
        f" id: \"{comment_id}\""
        " }) { discussion { id } } }"
    )
    r3 = gql(TOKEN2, mark_q)
    print(f"Done: {title[:60]}...")


if __name__ == "__main__":
    for title, answer in QA:
        create_qa(title, answer)
    print("All done.")
