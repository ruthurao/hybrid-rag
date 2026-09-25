from __future__ import annotations

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.generate import NO_HIT
from src.rag.index import persist_chunks
from src.rag.logging import configure_logging
from src.rag.query import SCOPE_COMPARE, SCOPE_DIAGNOSIS, SCOPE_LIVE, ask, cache_key


APPROVAL = "What is the invoice approval threshold?"


class CountingEmbedder:
    def __init__(self) -> None:
        self.inner = LexicalEmbeddingAdapter()
        self.model_name = self.inner.model_name
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return self.inner.embed(texts)


@pytest.fixture(scope="module")
def live_store(chunks):
    store = InMemoryVectorStore()
    persist_chunks(chunks, LexicalEmbeddingAdapter(), store, "test-run")
    return store


def _ask(store, query=APPROVAL, **kwargs):
    embedder = kwargs.pop("embedder", None) or LexicalEmbeddingAdapter()
    cache = kwargs.pop("cache", None) or InMemoryAnswerCache()
    return ask(
        query,
        embedder,
        store,
        ingest_run_id=kwargs.pop("ingest_run_id", "test-run"),
        cache=cache,
        **kwargs,
    )


def test_live_ask_hides_replaced_approval_rule(live_store):
    answer = _ask(live_store)
    record_ids = {cite["record_id"] for cite in answer.citations}
    assert "ap-us-0001-v2.0" in record_ids
    assert "ap-us-0001-v1.0" not in record_ids
    assert "$10,000" in answer.text
    assert "$7,500" not in answer.text
    assert all(cite["status"] == "current" for cite in answer.citations)


def test_citations_name_document_version_and_section(live_store):
    answer = _ask(live_store)
    assert answer.citations
    for cite in answer.citations:
        assert cite["doc_id"]
        assert cite["version"]
        assert cite["section"]


def test_every_answer_has_a_trace(live_store):
    answer = _ask(live_store, request_id="req-1")
    trace = answer.query_trace
    assert trace.request_id == "req-1"
    assert trace.ingest_run_id == "test-run"
    assert trace.cache_hit is False
    assert trace.pipeline_id == "rerank-v2"
    assert trace.chunk_ids
    assert "retrieve" in trace.latencies_ms


def test_repeat_ask_is_a_cache_hit_and_skips_retrieve(live_store):
    cache = InMemoryAnswerCache()
    embedder = CountingEmbedder()
    first = _ask(live_store, embedder=embedder, cache=cache)
    second = _ask(live_store, embedder=embedder, cache=cache, request_id="req-2")
    assert first.query_trace.cache_hit is False
    assert second.query_trace.cache_hit is True
    assert second.text == first.text
    assert second.citations == first.citations
    assert embedder.calls == 1
    assert second.query_trace.chunk_ids == first.query_trace.chunk_ids


def test_diagnosis_ask_misses_the_live_cache(live_store):
    cache = InMemoryAnswerCache()
    live = _ask(live_store, cache=cache, scope=SCOPE_LIVE)
    diagnosis = _ask(live_store, cache=cache, scope=SCOPE_DIAGNOSIS)
    assert live.query_trace.cache_hit is False
    assert diagnosis.query_trace.cache_hit is False
    record_ids = {cite["record_id"] for cite in diagnosis.citations}
    assert "ap-us-0001-v1.0" in record_ids or "$7,500" in diagnosis.text


def test_new_ingest_run_misses_the_old_cache(live_store):
    cache = InMemoryAnswerCache()
    _ask(live_store, cache=cache, ingest_run_id="run-a")
    second = _ask(live_store, cache=cache, ingest_run_id="run-b")
    assert second.query_trace.cache_hit is False


def test_empty_retrieve_is_not_cached():
    """Vector search still returns k hits when scores are low. An empty store
    is the real miss: nothing to cite, and nothing worth remembering."""
    cache = InMemoryAnswerCache()
    embedder = CountingEmbedder()
    empty = InMemoryVectorStore()
    first = _ask(empty, embedder=embedder, cache=cache)
    second = _ask(empty, embedder=embedder, cache=cache)
    assert first.text == NO_HIT
    assert first.citations == []
    assert second.query_trace.cache_hit is False
    assert embedder.calls == 2


def test_query_logs_ids_not_chunk_text(live_store, capsys, parse_log_lines):
    import structlog

    configure_logging()
    try:
        _ask(live_store, request_id="log-ask")
        stderr = capsys.readouterr().err
        assert "priya" not in stderr.lower()
        assert "EE-4419" not in stderr
        events = {row["event"]: row for row in parse_log_lines(stderr)}
        assert events["query.start"]["scope"] == SCOPE_LIVE
        assert "chunk_ids" in events["query.retrieve"]
        assert events["query.done"]["cache_hit"] is False
    finally:
        structlog.reset_defaults()


def test_cache_key_changes_with_pipeline_and_scope():
    live = cache_key(APPROVAL, SCOPE_LIVE, "run", "vector-v1")
    assert cache_key("  WHAT IS THE INVOICE APPROVAL THRESHOLD? ", SCOPE_LIVE, "run", "vector-v1") == live
    assert cache_key(APPROVAL, SCOPE_DIAGNOSIS, "run", "vector-v1") != live
    assert cache_key(APPROVAL, SCOPE_COMPARE, "run", "vector-v1") != live
    assert cache_key(APPROVAL, SCOPE_LIVE, "run", "hybrid-v1") != live
