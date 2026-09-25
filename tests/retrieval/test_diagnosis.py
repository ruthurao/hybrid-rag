from __future__ import annotations

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.ingestion.index import persist_chunks
from src.rag.retrieval.query import SCOPE_DIAGNOSIS, SCOPE_LIVE, ask


@pytest.fixture(scope="module")
def store(chunks):
    memory = InMemoryVectorStore()
    persist_chunks(chunks, LexicalEmbeddingAdapter(), memory, "test-run")
    return memory


def test_diagnosis_attributes_7500_to_replaced_ap_v1(store):
    """Part 6: the $7,500 figure is in the source data, not a model error.

    Fails if v1 was dropped from the index or filtered out of diagnosis.
    """
    answer = ask(
        "What invoice amount needs finance manager approval?",
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
        scope=SCOPE_DIAGNOSIS,
    )
    assert "ap-us-0001-v1.0#AP-5.1" in answer.query_trace.chunk_ids
    cite = next(c for c in answer.citations if c["record_id"] == "ap-us-0001-v1.0")
    assert cite["section"] == "AP-5.1"
    assert cite["status"] == "replaced"
    assert "$7,500" in answer.text


def test_live_does_not_pass_the_diagnosis_case(store):
    """The same question on the live path must not be allowed to hide the plant
    by looking like a success. Live simply must not cite v1."""
    answer = ask(
        "What invoice amount needs finance manager approval?",
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
        scope=SCOPE_LIVE,
    )
    assert "ap-us-0001-v1.0" not in {c["record_id"] for c in answer.citations}
    assert "$7,500" not in answer.text
