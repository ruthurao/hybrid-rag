from __future__ import annotations

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.config import default_settings
from src.rag.index import persist_chunks
from src.rag.logging import configure_logging
from src.rag.models import Chunk, Hit
from src.rag.query import ask
from src.rag.rerank import IdentityReranker

TABLE = "mec-us-0001-v1.0#MEC-5.1"
TRAVEL = "mec-us-0001-v1.0#MEC-8.2"
QUERY_6100 = "What is account code 6100 used for at travel close?"


class PreferTableReranker:
    """Puts the coding table first. Stands in for a CrossEncoder in tests."""

    model_name = "stub-prefer-table"

    def rerank(self, query: str, hits: list[Hit], top_n: int) -> list[Hit]:
        def key(hit: Hit) -> tuple[int, float]:
            table = 0 if hit.chunk.chunk_id == TABLE else 1
            return (table, -hit.score)

        ordered = sorted(hits, key=key)
        return [
            Hit(chunk=hit.chunk, score=float(len(ordered) - i), source="rerank")
            for i, hit in enumerate(ordered[:top_n])
        ]


@pytest.fixture(scope="module")
def store(chunks):
    memory = InMemoryVectorStore()
    persist_chunks(chunks, LexicalEmbeddingAdapter(), memory, "test-run")
    return memory


def test_identity_keeps_at_most_top_n():
    hits = [
        Hit(chunk=Chunk(f"c{i}", "t", {}), score=1.0 - i * 0.1)
        for i in range(10)
    ]
    kept = IdentityReranker().rerank("q", hits, top_n=4)
    assert [h.chunk.chunk_id for h in kept] == ["c0", "c1", "c2", "c3"]


def test_rerank_keeps_table_chunk_for_6100(store):
    answer = ask(
        QUERY_6100,
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
        reranker=PreferTableReranker(),
    )
    assert answer.query_trace.chunk_ids[0] == TABLE
    assert TRAVEL not in answer.query_trace.chunk_ids[:1]
    assert len(answer.query_trace.chunk_ids) <= default_settings().rerank_top_n
    assert "6100" in answer.text


def test_rerank_live_still_hides_replaced_ap(store):
    answer = ask(
        "What is the invoice approval threshold?",
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
        reranker=PreferTableReranker(),
    )
    records = {cite["record_id"] for cite in answer.citations}
    assert "ap-us-0001-v1.0" not in records


def test_rerank_logs_ids_not_chunk_text(store, capsys, parse_log_lines):
    import structlog

    configure_logging()
    try:
        ask(
            QUERY_6100,
            LexicalEmbeddingAdapter(),
            store,
            "test-run",
            cache=InMemoryAnswerCache(),
            reranker=PreferTableReranker(),
            request_id="rr-1",
        )
        stderr = capsys.readouterr().err
        events = {row["event"]: row for row in parse_log_lines(stderr)}
        row = events["query.rerank"]
        assert row["model"] == "stub-prefer-table"
        assert row["chunk_ids"][0] == TABLE
        assert len(row["chunk_ids"]) <= 4
        assert "priya" not in stderr.lower()
    finally:
        structlog.reset_defaults()
