from __future__ import annotations

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.retrieval.compare import detect_comparison_intent, mixed_versions
from src.rag.ingestion.index import persist_chunks
from src.rag.models import Chunk, Hit
from src.rag.retrieval.query import SCOPE_COMPARE, SCOPE_LIVE, ask


COMPARE = "What changed in the invoice approval threshold?"
LIVE = "What is the invoice approval threshold?"


@pytest.fixture(scope="module")
def store(chunks):
    memory = InMemoryVectorStore()
    persist_chunks(chunks, LexicalEmbeddingAdapter(), memory, "test-run")
    return memory


def _ask(store, query, **kwargs):
    return ask(
        query,
        kwargs.pop("embedder", None) or LexicalEmbeddingAdapter(),
        store,
        ingest_run_id=kwargs.pop("ingest_run_id", "test-run"),
        cache=kwargs.pop("cache", None) or InMemoryAnswerCache(),
        **kwargs,
    )


def test_explicit_phrasing_is_a_comparison():
    assert detect_comparison_intent("what changed in AP-5.1")
    assert detect_comparison_intent("old vs new approval policy")
    assert detect_comparison_intent("difference between the two versions")
    assert not detect_comparison_intent("what is the invoice approval threshold")
    assert not detect_comparison_intent("how does month-end lock work")


def test_compare_ask_cites_both_approval_rules(store):
    answer = _ask(store, COMPARE)
    assert answer.query_trace.scope == SCOPE_COMPARE
    records = {cite["record_id"] for cite in answer.citations}
    assert "ap-us-0001-v1.0" in records
    assert "ap-us-0001-v2.0" in records
    assert "$7,500" in answer.text
    assert "$10,000" in answer.text
    assert "Current" in answer.text
    assert "replaced" in answer.text.lower()
    assert "ap-us-0001-v1.0#AP-5.1" in answer.query_trace.chunk_ids
    assert "ap-us-0001-v2.0#AP-5.1" in answer.query_trace.chunk_ids


def test_live_ask_still_hides_the_replaced_rule(store):
    answer = _ask(store, LIVE)
    records = {cite["record_id"] for cite in answer.citations}
    assert "ap-us-0001-v1.0" not in records
    assert "$7,500" not in answer.text


def test_cached_live_answer_is_not_reused_for_compare(store):
    cache = InMemoryAnswerCache()
    live = _ask(store, LIVE, cache=cache)
    compare = _ask(store, COMPARE, cache=cache)
    assert live.query_trace.cache_hit is False
    assert compare.query_trace.cache_hit is False
    assert compare.query_trace.scope == SCOPE_COMPARE
    assert live.query_trace.scope == SCOPE_LIVE


def test_repeat_compare_ask_is_a_cache_hit(store):
    cache = InMemoryAnswerCache()
    first = _ask(store, COMPARE, cache=cache)
    second = _ask(store, COMPARE, cache=cache)
    assert first.query_trace.cache_hit is False
    assert second.query_trace.cache_hit is True
    assert second.citations == first.citations


def test_live_safety_net_drops_a_replaced_rule_that_slipped_in():
    current = Hit(
        chunk=Chunk(
            "v2",
            "$10,000",
            {"status": "current", "doc_id": "ap-us-0001", "version": "v2.0", "section": "AP-5.1", "record_id": "ap-us-0001-v2.0"},
        ),
        score=0.9,
    )
    replaced = Hit(
        chunk=Chunk(
            "v1",
            "$7,500",
            {"status": "replaced", "doc_id": "ap-us-0001", "version": "v1.0", "section": "AP-5.1", "record_id": "ap-us-0001-v1.0"},
        ),
        score=0.8,
    )
    assert mixed_versions([current, replaced])
    assert not mixed_versions([current])
