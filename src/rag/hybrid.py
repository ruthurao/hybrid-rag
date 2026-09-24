from __future__ import annotations

import re
from collections import defaultdict
from typing import Sequence

from src.rag.config import Settings, default_settings
from src.rag.models import Chunk, Hit
from src.rag.ports.store import VectorStoreAdapter

TOKEN = re.compile(r"[a-z0-9$]+")


def keyword_retrieve(query: str, chunks: Sequence[Chunk], k: int) -> list[Hit]:
    """Score chunks by how many query tokens they contain."""
    terms = set(TOKEN.findall(query.lower()))
    if not terms:
        return []
    hits: list[Hit] = []
    for chunk in chunks:
        text = chunk.text.lower()
        overlap = sum(1 for term in terms if term in text)
        if overlap:
            hits.append(Hit(chunk=chunk, score=float(overlap), source="keyword"))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k]


def rrf_fuse(ranked_lists: Sequence[Sequence[Hit]], rrf_k: int) -> list[Hit]:
    """Reciprocal rank fusion. A chunk that is high on two lists beats one list."""
    scores: dict[str, float] = defaultdict(float)
    chunks: dict[str, Chunk] = {}
    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.chunk.chunk_id] += 1.0 / (rrf_k + rank)
            chunks[hit.chunk.chunk_id] = hit.chunk
    fused = [
        Hit(chunk=chunks[chunk_id], score=score, source="hybrid")
        for chunk_id, score in scores.items()
    ]
    fused.sort(key=lambda h: h.score, reverse=True)
    return fused


def hybrid_retrieve(
    query: str,
    vector: Sequence[float],
    store: VectorStoreAdapter,
    where: dict | None,
    settings: Settings | None = None,
) -> tuple[list[Hit], list[Hit], list[Hit]]:
    """Vector list, keyword list, RRF fusion (truncated to vector_top_k)."""
    settings = settings or default_settings()
    vector_hits = store.query(vector, k=settings.vector_top_k, where=where)
    keyword_hits = keyword_retrieve(
        query, store.get_all(where=where), settings.keyword_top_k
    )
    fused = rrf_fuse([vector_hits, keyword_hits], settings.rrf_k)
    return vector_hits, keyword_hits, fused[: settings.vector_top_k]
