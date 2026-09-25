from __future__ import annotations

from collections import defaultdict

from src.rag.config import Settings, default_settings
from src.rag.models import Hit
from src.rag.ports.store import VectorStoreAdapter


def detect_comparison_intent(query: str, settings: Settings | None = None) -> bool:
    """True when the question asks for more than the rule now in force."""
    settings = settings or default_settings()
    haystack = f" {query.lower()} "
    return any(signal in haystack for signal in settings.comparison_signals)


def mixed_versions(hits: list[Hit]) -> bool:
    statuses = {hit.chunk.metadata.get("status") for hit in hits}
    return "current" in statuses and "replaced" in statuses


def retrieve_both_versions(
    vector: list[float],
    store: VectorStoreAdapter,
    settings: Settings | None = None,
) -> list[Hit]:
    """Pull top-k from each version of one document.

    Ranking is not asked to surface both. Each record_id is queried on its
    own, which is why AP v1 stays findable next to AP v2.
    """
    settings = settings or default_settings()
    rank = {"authority_rank": {"$gte": settings.live_authority_rank}}
    catalog = _versioned_records(store, rank)
    if not catalog:
        return store.query(vector, k=settings.vector_top_k, where=rank)
    scored = store.query(vector, k=settings.vector_top_k, where=rank)
    doc_id = _pick_doc(scored, catalog)
    if doc_id is None:
        return scored
    hits: list[Hit] = []
    for record_id in sorted(catalog[doc_id]):
        hits.extend(
            store.query(
                vector,
                k=settings.compare_k_per_version,
                where={"$and": [rank, {"record_id": {"$eq": record_id}}]},
            )
        )
    for hit in hits:
        hit.source = "compare"
    return hits


def _versioned_records(store: VectorStoreAdapter, rank: dict) -> dict[str, set[str]]:
    by_doc: dict[str, set[str]] = defaultdict(set)
    for chunk in store.get_all(where=rank):
        doc_id = chunk.metadata.get("doc_id")
        record_id = chunk.metadata.get("record_id")
        if doc_id and record_id:
            by_doc[str(doc_id)].add(str(record_id))
    return {doc: records for doc, records in by_doc.items() if len(records) > 1}


def _pick_doc(hits: list[Hit], catalog: dict[str, set[str]]) -> str | None:
    for hit in hits:
        doc_id = str(hit.chunk.metadata.get("doc_id") or "")
        if doc_id in catalog:
            return doc_id
    return next(iter(catalog), None)
