"""Semantic + structural matcher for aligning old/new clause trees."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

import numpy as np

from app.diff.segmentor import ClauseNode


class MatchType(str, Enum):
    ID_MATCH = "id_match"         # same section number/id
    SEMANTIC = "semantic"         # embedding similarity
    UNMATCHED = "unmatched"


@dataclass
class ClauseMatch:
    old_node: ClauseNode | None
    new_node: ClauseNode | None
    match_type: MatchType
    similarity: float | None


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def _embed(texts: list[str], model_name: str) -> np.ndarray:
    if not texts:
        return np.array([])
    model = _load_model(model_name)
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


def match_clauses(
    old_nodes: list[ClauseNode],
    new_nodes: list[ClauseNode],
    model_name: str,
    similarity_threshold: float,
) -> list[ClauseMatch]:
    """Match old clauses to new clauses using ID-first, then semantic fallback."""
    matches: list[ClauseMatch] = []
    matched_old: set[str] = set()
    matched_new: set[str] = set()

    # Pass 1: exact ID match
    old_by_id = {n.id: n for n in old_nodes}
    new_by_id = {n.id: n for n in new_nodes}
    for node_id, old_node in old_by_id.items():
        if node_id in new_by_id:
            new_node = new_by_id[node_id]
            sim = _text_similarity(old_node.text, new_node.text, model_name)
            matches.append(ClauseMatch(old_node, new_node, MatchType.ID_MATCH, sim))
            matched_old.add(node_id)
            matched_new.add(node_id)

    # Pass 2: semantic matching for unmatched nodes
    unmatched_old = [n for n in old_nodes if n.id not in matched_old]
    unmatched_new = [n for n in new_nodes if n.id not in matched_new]

    if unmatched_old and unmatched_new:
        old_texts = [n.full_text[:512] for n in unmatched_old]
        new_texts = [n.full_text[:512] for n in unmatched_new]
        old_embs = _embed(old_texts, model_name)
        new_embs = _embed(new_texts, model_name)

        if old_embs.ndim == 2 and new_embs.ndim == 2:
            sim_matrix = old_embs @ new_embs.T
            claimed_new: set[int] = set()
            for oi, old_node in enumerate(unmatched_old):
                best_ni = int(np.argmax(sim_matrix[oi]))
                best_sim = float(sim_matrix[oi, best_ni])
                if best_sim >= similarity_threshold and best_ni not in claimed_new:
                    matches.append(ClauseMatch(
                        old_node, unmatched_new[best_ni],
                        MatchType.SEMANTIC, best_sim,
                    ))
                    matched_old.add(old_node.id)
                    matched_new.add(unmatched_new[best_ni].id)
                    claimed_new.add(best_ni)

    # Remaining unmatched
    for n in old_nodes:
        if n.id not in matched_old:
            matches.append(ClauseMatch(n, None, MatchType.UNMATCHED, None))
    for n in new_nodes:
        if n.id not in matched_new:
            matches.append(ClauseMatch(None, n, MatchType.UNMATCHED, None))

    return matches


def _text_similarity(a: str, b: str, model_name: str) -> float:
    if not a or not b:
        return 0.0
    embs = _embed([a[:512], b[:512]], model_name)
    if embs.ndim == 2 and len(embs) == 2:
        return float(np.dot(embs[0], embs[1]))
    return 0.0
