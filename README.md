# LegaLens

> Semantic diff engine for legal documents — clause-level meaning shifts and risk scoring.

[![CI](https://github.com/Aliipou/legalens/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/legalens/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Problem

Legal document review is a manual, time-intensive process. When contracts go through revision cycles, lawyers compare versions line-by-line — but clause-level semantic drift is invisible without NLP. A sentence can change meaning entirely while remaining syntactically similar: "Party A shall pay within 30 days" becoming "Party A may pay within 90 days" rewrites an obligation into a discretionary act and extends the deadline by three months. No traditional diff tool catches this as a legal risk. LegaLens was built to make that kind of change explicit, categorised, and scored.

---

## Architecture

```
Document Ingestion
  |
  v
Segmentor          Parse document into hierarchical clause tree
  |                (sections, (a)(b) subclauses, bullets, preamble)
  v
Sentence Embeddings   all-MiniLM-L6-v2 via sentence-transformers
  |
  v
Clause Alignment   ID-first match by section number; semantic cosine
  |                similarity fallback for unnumbered/reordered clauses
  v
Drift Detection    15+ deterministic legal rules fire on each clause pair
  |                (obligation shift, liability, penalties, deadlines,
  |                 arbitration, jurisdiction, exclusivity, waiver, indemnity)
  v
Risk Scoring       Hybrid: semantic 30% + rules 55% + structural 15%
  |                -> combined 0-100 -> level: low / medium / high / critical
  v
FastAPI            /v1/diff  /v1/diff/upload  /v1/risk-terms
  |
  v
Next.js 14         Clause cards, risk breakdown panel, filter bar
```

---

## Decisions

**Why sentence-transformers (all-MiniLM-L6-v2)?**
Domain-agnostic embeddings that work well for English legal text without fine-tuning. The model runs fully offline with no API calls, keeping document content private. It is fast enough for clause-pair comparisons in a request cycle.

**Why cosine similarity for alignment?**
Clause matching requires a symmetric comparison — it does not matter which document is "source" and which is "target". Cosine similarity is symmetric, bounded [0, 1], and well-understood. It is used as a fallback only; section-number matching is always preferred when available, since two clauses with the same identifier should be compared regardless of semantic drift.

**Why clause-level rather than document-level?**
Document-level embeddings average out everything, hiding localised changes. A contract can be 98% unchanged with one critical clause rewritten. Clause-level granularity surfaces the specific paragraph, its rule hits, and its individual risk score — giving a lawyer the exact location and nature of the change.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (Python 3.12), uvicorn |
| Embeddings | sentence-transformers, all-MiniLM-L6-v2 |
| Rule engine | Deterministic regex + pattern matching (15+ rules) |
| Storage | PostgreSQL 16 + SQLAlchemy async + asyncpg |
| Migrations | Alembic |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Reverse proxy | nginx |
| Monitoring | Prometheus + Grafana + Loki |
| Infra | Terraform -> Azure (VNet, PostgreSQL Flexible Server, ACR, App Service, CDN) |
| Orchestration | Kubernetes (HPA 2-8 replicas) |
| CI/CD | GitHub Actions (lint, test, Trivy scan, Azure deploy) |

---

## Running Locally

**Requirements:** Python 3.12+, Docker (optional for full stack)

### API only

```bash
git clone https://github.com/Aliipou/legalens
cd legalens
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API.

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

### Running tests

```bash
pytest tests/ -q
# 45 passed in ~1.5s (uses deterministic embedding mock — no GPU or network required)
```

---

## Known Limitations

- **English-only.** The rule engine patterns and the embedding model are tuned for English legal text. Other languages will produce unpredictable rule matches.
- **No OCR for PDFs.** Input is plain text or `.txt` files. Scanned PDFs are not supported; they must be converted externally before submission.
- **No court-specific training.** The risk weights and rules are generic contract heuristics. Jurisdiction-specific concepts (e.g. UK indemnity conventions vs. US) are not differentiated.
- **Similarity threshold is fixed.** The clause-alignment cosine threshold (default 0.85) is a single global value. Highly technical sections with dense jargon may require tuning.

---

## License

MIT
