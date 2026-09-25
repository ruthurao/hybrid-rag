from __future__ import annotations

import time
from uuid import uuid4

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.retrieval.compare import detect_comparison_intent, mixed_versions, retrieve_both_versions
from src.rag.config import Settings, default_settings
from src.rag.generation.generate import ExtractiveGenerator
from src.rag.retrieval.hybrid import hybrid_retrieve
from src.rag.logging import get_logger
from src.rag.models import Answer, QueryTrace
from src.rag.ports.cache import AnswerCache
from src.rag.ports.embedder import EmbeddingAdapter
from src.rag.ports.generator import Generator
from src.rag.ports.rerank import Reranker
from src.rag.ports.store import VectorStoreAdapter
from src.rag.retrieval.rerank import IdentityReranker

SCOPE_LIVE = "live"
SCOPE_DIAGNOSIS = "diagnosis"
SCOPE_COMPARE = "compare"


def cache_key(query: str, scope: str, ingest_run_id: str, pipeline_id: str) -> str:
    return f"{pipeline_id}|{scope}|{ingest_run_id}|{_normalize(query)}"


def retrieve_filter(scope: str, settings: Settings) -> dict:
    rank = {"authority_rank": {"$gte": settings.live_authority_rank}}
    if scope in (SCOPE_DIAGNOSIS, SCOPE_COMPARE):
        return rank
    return {"$and": [{"status": {"$eq": settings.live_status}}, rank]}


def ask(
    query: str,
    embedder: EmbeddingAdapter,
    store: VectorStoreAdapter,
    ingest_run_id: str,
    cache: AnswerCache | None = None,
    settings: Settings | None = None,
    scope: str = SCOPE_LIVE,
    request_id: str | None = None,
    reranker: Reranker | None = None,
    generator: Generator | None = None,
) -> Answer:
    """Cache, then hybrid retrieve (or per-version compare), then generate.

    A hit returns the stored answer and citations. A miss never writes an
    empty answer, so a later ingest can still fill the gap. The default
    generator pastes chunk text. A failed generator raises and is not cached.
    """
    settings = settings or default_settings()
    cache = cache or InMemoryAnswerCache()
    reranker = reranker or IdentityReranker()
    generator = generator or ExtractiveGenerator()
    request_id = request_id or uuid4().hex
    started = time.perf_counter()
    if detect_comparison_intent(query, settings):
        scope = SCOPE_COMPARE
    where = retrieve_filter(scope, settings)
    key = cache_key(query, scope, ingest_run_id, settings.pipeline_id)
    log = get_logger(request_id=request_id, ingest_run_id=ingest_run_id)
    log.info("query.start", scope=scope, pipeline_id=settings.pipeline_id)

    cached = cache.get(key)
    if cached is not None:
        prior = cached.query_trace
        trace = QueryTrace(
            request_id=request_id,
            ingest_run_id=ingest_run_id,
            embedding_model=embedder.model_name,
            pipeline_id=settings.pipeline_id,
            scope=scope,
            cache_hit=True,
            filter=where,
            k=settings.vector_top_k,
            chunk_ids=list(prior.chunk_ids),
            scores=list(prior.scores),
            sources=list(prior.sources),
            vector_ids=list(prior.vector_ids),
            latencies_ms={
                "retrieve": 0.0,
                "generate": 0.0,
                "total": round((time.perf_counter() - started) * 1000, 3),
            },
        )
        log.info("query.done", cache_hit=True, citation_count=len(cached.citations))
        return Answer(text=cached.text, citations=cached.citations, query_trace=trace)

    retrieve_started = time.perf_counter()
    vector = embedder.embed([query])[0]
    if scope == SCOPE_COMPARE:
        hits = retrieve_both_versions(vector, store, settings)
        vector_ids = [hit.chunk.chunk_id for hit in hits]
    else:
        vector_hits, keyword_hits, hits = hybrid_retrieve(
            query, vector, store, where, settings
        )
        vector_ids = [hit.chunk.chunk_id for hit in vector_hits]
        log.info(
            "query.hybrid",
            vector_ids=[hit.chunk.chunk_id for hit in vector_hits],
            keyword_ids=[hit.chunk.chunk_id for hit in keyword_hits],
            fused_ids=[hit.chunk.chunk_id for hit in hits],
        )
        if scope == SCOPE_LIVE and mixed_versions(hits):
            hits = [
                hit
                for hit in hits
                if hit.chunk.metadata.get("status") == settings.live_status
            ]
        hits = reranker.rerank(query, hits, settings.rerank_top_n)
        log.info(
            "query.rerank",
            model=reranker.model_name,
            hit_count=len(hits),
            chunk_ids=[hit.chunk.chunk_id for hit in hits],
            scores=[round(hit.score, 4) for hit in hits],
        )
    retrieve_ms = (time.perf_counter() - retrieve_started) * 1000
    log.info(
        "query.retrieve",
        hit_count=len(hits),
        chunk_ids=[hit.chunk.chunk_id for hit in hits],
        scores=[round(hit.score, 4) for hit in hits],
    )

    generate_started = time.perf_counter()
    text, citations = generator.generate(query, hits, compare=scope == SCOPE_COMPARE)
    generate_ms = (time.perf_counter() - generate_started) * 1000
    log.info(
        "query.generate",
        model=generator.model_name,
        citation_count=len(citations),
        empty=not hits,
    )

    trace = _trace(
        request_id=request_id,
        ingest_run_id=ingest_run_id,
        embedding_model=embedder.model_name,
        settings=settings,
        scope=scope,
        cache_hit=False,
        where=where,
        hits=hits,
        vector_ids=vector_ids,
        retrieve_ms=retrieve_ms,
        generate_ms=generate_ms,
        started=started,
    )
    answer = Answer(text=text, citations=citations, query_trace=trace)
    if hits and text.strip():
        cache.set(key, answer)
    log.info("query.done", cache_hit=False, citation_count=len(citations))
    return answer


def _normalize(query: str) -> str:
    return " ".join(query.lower().split())


def _trace(*, request_id, ingest_run_id, embedding_model, settings, scope, cache_hit, where, hits, vector_ids, retrieve_ms, generate_ms, started) -> QueryTrace:
    return QueryTrace(
        request_id=request_id,
        ingest_run_id=ingest_run_id,
        embedding_model=embedding_model,
        pipeline_id=settings.pipeline_id,
        scope=scope,
        cache_hit=cache_hit,
        filter=where,
        k=settings.vector_top_k,
        chunk_ids=[hit.chunk.chunk_id for hit in hits],
        scores=[hit.score for hit in hits],
        sources=[hit.source for hit in hits],
        vector_ids=list(vector_ids),
        latencies_ms={
            "retrieve": round(retrieve_ms, 3),
            "generate": round(generate_ms, 3),
            "total": round((time.perf_counter() - started) * 1000, 3),
        },
    )
