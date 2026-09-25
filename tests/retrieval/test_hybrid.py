from __future__ import annotations

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.retrieval.hybrid import hybrid_retrieve, keyword_retrieve, rrf_fuse
from src.rag.ingestion.index import persist_chunks
from src.rag.logging import configure_logging
from src.rag.models import Chunk, Hit
from src.rag.retrieval.query import SCOPE_LIVE, ask, retrieve_filter
from src.rag.config import default_settings

TABLE = "mec-us-0001-v1.0#MEC-5.1"
TRAVEL = "mec-us-0001-v1.0#MEC-8.2"
QUERY_6100 = "What is account code 6100 used for at travel close?"


@pytest.fixture(scope="module")
def store(chunks):
    memory = InMemoryVectorStore()
    persist_chunks(chunks, LexicalEmbeddingAdapter(), memory, "test-run")
    return memory


def _hit(chunk_id: str, text: str = "x") -> Hit:
    return Hit(chunk=Chunk(chunk_id, text, {}), score=0.0, source="vector")


def test_rrf_promotes_the_chunk_that_keyword_ranks_first():
    """Vector puts travel first; keyword puts the table first and omits
    travel. Fusion must not leave the table behind the travel prose."""
    vector = [_hit(TRAVEL), _hit("other"), _hit(TABLE)]
    keyword = [_hit(TABLE)]
    fused = rrf_fuse([vector, keyword], rrf_k=60)
    assert fused[0].chunk.chunk_id == TABLE
    assert fused[0].source == "hybrid"


def test_keyword_retrieve_finds_6100_only_in_the_table(store):
    hits = keyword_retrieve(QUERY_6100, store.get_all(), k=10)
    with_code = [hit.chunk.chunk_id for hit in hits if "6100" in hit.chunk.text]
    assert with_code == [TABLE]
    assert hits[0].chunk.chunk_id == TABLE
    travel_rank = next(
        i for i, hit in enumerate(hits) if hit.chunk.chunk_id == TRAVEL
    )
    assert travel_rank > 0


def test_lexical_vector_already_ranks_the_table_first(store):
    """The 12-pt contrast is a MiniLM effect. Bag-of-words sees 6100 and
    already prefers the table — do not pretend otherwise in this suite."""
    settings = default_settings()
    where = retrieve_filter(SCOPE_LIVE, settings)
    vector = LexicalEmbeddingAdapter().embed([QUERY_6100])[0]
    vector_hits, _, fused = hybrid_retrieve(QUERY_6100, vector, store, where, settings)
    assert vector_hits[0].chunk.chunk_id == TABLE
    assert fused[0].chunk.chunk_id == TABLE


def test_hybrid_live_path_still_hides_replaced_ap(store):
    answer = ask(
        "What is the invoice approval threshold?",
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
    )
    records = {cite["record_id"] for cite in answer.citations}
    assert "ap-us-0001-v1.0" not in records
    assert "$7,500" not in answer.text


def test_hybrid_logs_three_id_lists_not_chunk_text(store, capsys, parse_log_lines):
    import structlog

    configure_logging()
    try:
        ask(
            QUERY_6100,
            LexicalEmbeddingAdapter(),
            store,
            "test-run",
            cache=InMemoryAnswerCache(),
            request_id="hyb-1",
        )
        stderr = capsys.readouterr().err
        events = {row["event"]: row for row in parse_log_lines(stderr)}
        hybrid = events["query.hybrid"]
        assert TABLE in hybrid["keyword_ids"]
        assert TABLE in hybrid["fused_ids"]
        assert "priya" not in stderr.lower()
    finally:
        structlog.reset_defaults()


def test_pipeline_id_is_hybrid(store):
    answer = ask(
        "What is the invoice approval threshold?",
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
    )
    assert answer.query_trace.pipeline_id == "rerank-v2"
