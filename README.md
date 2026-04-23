# LegaLens

> Semantic diff engine for legal documents — find what changed, and why it matters.

[![CI](https://github.com/Aliipou/legalens/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/legalens/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**LegaLens** uses sentence-transformer embeddings to semantically diff legal documents — not just character-level changes, but clause-level meaning shifts. It flags added/removed/modified clauses, scores semantic risk, and highlights high-stakes terms like *indemnification*, *arbitration*, and *liability waivers*.

## Why Not Just `diff`?

A standard text diff treats any rewording as a change — it can't tell whether "Company shall not be liable" and "The company bears no liability" are the same clause. LegaLens compares clause *meaning*, not bytes.

## Features

- **Semantic clause matching** via `sentence-transformers` (all-MiniLM-L6-v2 by default)
- **Risk scoring**: each modified clause gets a `low / medium / high` semantic risk rating
- **High-risk term detection**: flags changes near indemnification, termination, arbitration, warranty, etc.
- **Two input modes**: JSON body or multipart file upload
- **Docker-ready**: single-container deployment, no external dependencies
- **OpenAPI docs**: `/docs` with live try-it UI

## Quick Start

```bash
git clone https://github.com/Aliipou/legalens
cd legalens
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs)

### Docker

```bash
docker build -t legalens .
docker run -p 8000:8000 legalens
```

## API

### `POST /v1/diff` — JSON

```json
{
  "old_document": "Party A agrees to pay Party B within 30 days.",
  "new_document": "Party A agrees to pay Party B within 90 days. Failure to pay incurs a 5% penalty.",
  "similarity_threshold": 0.85
}
```

**Response:**

```json
{
  "total_clauses_old": 1,
  "total_clauses_new": 1,
  "added": 0,
  "removed": 0,
  "modified": 1,
  "unchanged": 0,
  "overall_risk": "high",
  "summary": "0 clause(s) added, 0 removed, 1 modified. Overall risk: high.",
  "diffs": [
    {
      "change_type": "modified",
      "similarity": 0.71,
      "semantic_risk": "high",
      "key_changes": ["+penalty"],
      "summary": "Clause modified (similarity=0.71): risk=high"
    }
  ]
}
```

### `POST /v1/diff/upload` — File Upload

```bash
curl -X POST http://localhost:8000/v1/diff/upload \
  -F "old_file=@contract_v1.txt" \
  -F "new_file=@contract_v2.txt"
```

### `GET /v1/risk-terms`

Returns the list of tracked high-risk legal terms.

## Risk Scoring

| Similarity | Risk |
|---|---|
| ≥ 0.95 | Low |
| 0.80 – 0.95 | Medium |
| < 0.80 | High |

Clauses containing terms like *indemnification*, *termination*, *arbitration*, *waiver*, *perpetual*, or *irrevocable* get extra scrutiny in the key changes list.

## License

MIT
