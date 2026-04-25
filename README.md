# LegaLens

> Legal reasoning and change intelligence engine — not just a diff tool.

[![CI](https://github.com/Aliipou/legalens/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/legalens/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

LegaLens combines sentence-transformer embeddings with a deterministic legal rule engine to detect what changed in a contract — and *why it matters*. It segments documents into hierarchical clauses, matches them across versions, fires 15+ legal rules on each change, and outputs a hybrid risk score with full explainability.

## Why Not Just `diff`?

`diff` sees characters. LegaLens sees obligations.

It recognises that *"Party A shall pay within 30 days"* becoming *"Party A may pay within 90 days"* is not a typo — it is an obligation weakening (`shall → may`) combined with a deadline extension (30 → 90 days), producing a `critical` risk score with two named rule hits.

---

## Architecture

```
Request
  │
  ▼
Segmentor          Parse document into hierarchical clause tree
  │                (sections, (a)(b) subclauses, bullet lists, preamble)
  ▼
Matcher            ID-first match by section number, semantic fallback
  │                via sentence-transformers cosine similarity
  ▼
Rule Engine        15+ deterministic legal rules fire on each clause pair
  │                (obligation shift, liability, penalties, deadlines,
  │                 arbitration, jurisdiction, exclusivity, waiver, indemnity)
  ▼
Risk Scorer        Hybrid score: semantic 30% + rules 55% + structural 15%
  │                → combined 0–100 → level: low / medium / high / critical
  ▼
FastAPI            /v1/diff  /v1/diff/upload  /v1/risk-terms
  │
  ▼
Next.js 14         Diff interface with clause cards, risk breakdown, filter bar
```

---

## Detected Risk Patterns

| Rule | Severity | Example |
|------|----------|---------|
| `obligation.shall_to_may` | **CRITICAL** | "shall pay" → "may pay" |
| `liability.shield_removed` | **CRITICAL** | "not be liable" removed |
| `dispute.arbitration_added` | **CRITICAL** | New binding arbitration clause |
| `rights.waiver_added` | **CRITICAL** | "hereby waives all rights" |
| `scope.irrevocable_added` | **CRITICAL** | "irrevocable perpetual" added |
| `penalty.amount_change` | **HIGH** | $10,000 → $100,000 |
| `rights.indemnity_added` | **HIGH** | New indemnification obligation |
| `term.termination_added` | **HIGH** | Termination clause added |
| `deadline.changed` | **MEDIUM/HIGH** | 30 days → 90 days |
| `dispute.jurisdiction_changed` | **HIGH** | Governing law modified |

---

## Quick Start

```bash
git clone https://github.com/Aliipou/legalens
cd legalens
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open **[http://localhost:8000/docs](http://localhost:8000/docs)** for the interactive API.

### Full stack (Docker)

```bash
docker compose up
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| API | http://localhost/v1/ |
| API docs | http://localhost/docs |
| Grafana | http://localhost:3001 |

---

## API

### `POST /v1/diff`

```bash
curl -X POST http://localhost:8000/v1/diff \
  -H "Content-Type: application/json" \
  -d '{
    "old_document": "Party A shall pay within 30 days.",
    "new_document": "Party A may pay within 90 days. Late payment incurs a 5% penalty."
  }'
```

```json
{
  "overall_risk": "critical",
  "summary": "0 added, 0 removed, 1 modified. Overall risk: critical. 1 critical change(s).",
  "diffs": [{
    "change_type": "modified",
    "similarity": 0.72,
    "risk": {
      "semantic_score": 28.0,
      "rule_score": 85,
      "structural_score": 30,
      "combined": 63.6,
      "level": "critical",
      "drivers": [
        "[CRITICAL] Mandatory obligation ('shall') replaced with discretionary language ('may')",
        "[HIGH] Financial amounts changed",
        "[HIGH] Deadline extended: 30 → 90 days"
      ]
    },
    "rule_hits": [
      {"rule_id": "obligation.shall_to_may", "severity": "critical"},
      {"rule_id": "penalty.added", "severity": "high"},
      {"rule_id": "deadline.changed", "severity": "high"}
    ]
  }]
}
```

### `POST /v1/diff/upload`

```bash
curl -X POST http://localhost:8000/v1/diff/upload \
  -F "old_file=@contract_v1.txt" \
  -F "new_file=@contract_v2.txt"
```

---

## Risk Score Model

```
combined = semantic_distance × 0.30
         + rule_score        × 0.55
         + structural_score  × 0.15

level:  < 20  → low
       20–45  → medium
       45–70  → high
        > 70  → critical
```

Structural score is boosted for sections with headings matching liability, payment, termination, or arbitration keywords.

---

## Infrastructure

```
legalens/
├── app/                  FastAPI backend
│   ├── diff/             Segmentor, Matcher, Rule Engine, Risk Scorer
│   ├── database/         SQLAlchemy async + Alembic migrations
│   ├── middleware.py      Rate limiting, security headers, request IDs
│   └── routers/          API endpoints
├── frontend/             Next.js 14 + TypeScript + Tailwind
├── nginx/                Reverse proxy, rate limiting, CDN cache headers
├── monitoring/           Prometheus + Grafana + Loki
├── infra/                Terraform → Azure (VNet, PostgreSQL, ACR, App Service, CDN)
├── k8s/                  Kubernetes manifests with HPA (2–8 replicas)
├── scripts/              pg_dump backup + restore with S3/Azure Blob upload
└── .github/workflows/    CI (test + lint + container + Trivy) / CD (Azure deploy)
```

---

## Tests

```bash
pytest tests/ -q
# 45 passed in 1.47s
```

All 45 tests run against a deterministic embedding mock — no model download required, no GPU, no network. Tests cover:

- Clause segmentation (numbered sections, lettered subclauses, bullets, preamble)
- All 15 legal rules with edge cases
- Engine integration (added, removed, modified, unchanged clauses)
- Risk score bounds, driver generation, summary correctness

---

## Deployment

### Render / Railway

Set `DATABASE_URL` and deploy. The app reads `postgres://` and rewrites it to `postgresql+asyncpg://` automatically.

### Azure (Terraform)

```bash
cd infra
terraform init
terraform apply -var="db_admin_password=<secret>"
```

Provisions: VNet + subnets, PostgreSQL Flexible Server, Container Registry, App Service (API + frontend), CDN endpoint with static asset caching.

### Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

HPA scales API pods 2–8 based on CPU (70%) and memory (80%).

---

## License

MIT
