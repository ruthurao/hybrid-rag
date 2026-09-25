from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Sequence

from src.rag.config import Settings, default_settings
from src.rag.models import Chunk, Hit
from src.rag.ports.store import VectorStoreAdapter

TOKEN = re.compile(r"[a-z0-9$]+")
# Interrogatives and prepositions match too many policy sentences.
# Digit tokens (6100, $75) are the hybrid signal; they get a higher weight.
_STOP = frozenset({"what", "which", "who", "how", "for", "the", "and", "are", "was", "used"})


def _keep(term: str) -> bool:
    if term in _STOP:
        return False
    return term.isdigit() or term.startswith("$") or len(term) >= 3


def _term_weight(term: str, n: int, df: int) -> float:
    idf = math.log((n + 1) / (df + 1)) + 1.0
    if any(ch.isdigit() for ch in term):
        return idf * 4.0
    return idf


def _tokens(text: str) -> set[str]:
    return {term for term in TOKEN.findall(text.lower()) if _keep(term)}


def keyword_retrieve(query: str, chunks: Sequence[Chunk], k: int) -> list[Hit]:
    """Score chunks by IDF-weighted query-token overlap.

    Substring overlap treated "at" as a hit inside "travel" and tied every
    close-related section at 7. Token + IDF lets 6100 lift the table.
    """
    terms = _tokens(query)
    if not terms:
        return []
    tokenized = [(chunk, _tokens(chunk.text)) for chunk in chunks]
    df: dict[str, int] = defaultdict(int)
    for _, toks in tokenized:
        for term in terms:
            if term in toks:
                df[term] += 1
    n = max(len(tokenized), 1)
    hits: list[Hit] = []
    for chunk, toks in tokenized:
        matched = terms & toks
        if not matched:
            continue
        score = sum(_term_weight(term, n, df[term]) for term in matched)
        hits.append(Hit(chunk=chunk, score=score, source="keyword"))
    hits.sort(key=lambda h: (-h.score, h.chunk.chunk_id))
    return hits[:k]


def rrf_fuse(ranked_lists: Sequence[Sequence[Hit]], rrf_k: int) -> list[Hit]:
    """Reciprocal rank fusion. A chunk that is high on two lists beats one list.

    Equal RRF scores break toward the first list's later ranks being worse,
    then toward the second list (keyword) rank so a table that keyword owns
    wins a tie against travel prose that vector owns.
    """
    scores: dict[str, float] = defaultdict(float)
    chunks: dict[str, Chunk] = {}
    keyword_rank: dict[str, int] = {}
    if len(ranked_lists) > 1:
        keyword_rank = {
            hit.chunk.chunk_id: rank
            for rank, hit in enumerate(ranked_lists[1], start=1)
        }
    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.chunk.chunk_id] += 1.0 / (rrf_k + rank)
            chunks[hit.chunk.chunk_id] = hit.chunk
    fused = [
        Hit(chunk=chunks[chunk_id], score=score, source="hybrid")
        for chunk_id, score in scores.items()
    ]
    fused.sort(
        key=lambda h: (
            -h.score,
            keyword_rank.get(h.chunk.chunk_id, 10**9),
            h.chunk.chunk_id,
        )
    )
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
