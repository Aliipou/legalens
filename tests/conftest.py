"""Patch sentence-transformers model loading so tests run without GPU/download."""
from unittest.mock import MagicMock

import numpy as np
import pytest


def _fake_embed(texts: list[str], model_name: str) -> np.ndarray:
    """Return deterministic unit vectors based on text hash — no model needed."""
    vecs = []
    for t in texts:
        seed = hash(t) % (2**31)
        r = np.random.default_rng(seed)
        v = r.standard_normal(384).astype(np.float32)
        v /= np.linalg.norm(v) + 1e-9
        vecs.append(v)
    return np.array(vecs)


@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    monkeypatch.setattr("app.diff.matcher._embed", _fake_embed)
    # Also patch lru_cache'd model loader so it never runs
    monkeypatch.setattr("app.diff.matcher._load_model", lambda name: MagicMock())
