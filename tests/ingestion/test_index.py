from __future__ import annotations

from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import ChromaVectorStore, InMemoryVectorStore
from src.rag.ingestion.index import persist_chunks
from src.rag.logging import configure_logging


def _persist(chunks, store=None, run_id: str = "idx-run"):
    store = store or InMemoryVectorStore()
    persisted = persist_chunks(chunks, LexicalEmbeddingAdapter(), store, run_id)
    return store, persisted


def _by_id(chunks):
    return {chunk.chunk_id: chunk for chunk in chunks}


def test_upsert_is_idempotent_by_chunk_id(chunks):
    store, first = _persist(chunks)
    assert store.count() == 44
    _, second = _persist(chunks, store)
    assert store.count() == 44
    assert [c.chunk_id for c in first] == [c.chunk_id for c in second]


def test_both_approval_rules_survive_the_store(chunks):
    store, _ = _persist(chunks)
    stored = _by_id(store.get_all())
    v1 = stored["ap-us-0001-v1.0#AP-5.1"]
    v2 = stored["ap-us-0001-v2.0#AP-5.1"]
    assert "$7,500" in v1.text and v1.metadata["status"] == "replaced"
    assert "$10,000" in v2.text and v2.metadata["status"] == "current"


def test_account_code_is_still_in_one_chunk(chunks):
    store, _ = _persist(chunks)
    with_code = [c.chunk_id for c in store.get_all() if "6100" in c.text]
    assert with_code == ["mec-us-0001-v1.0#MEC-5.1"]


def test_every_stored_chunk_names_its_embedder(chunks):
    _, persisted = _persist(chunks)
    for chunk in persisted:
        assert chunk.embedding
        assert chunk.metadata["embedding_model"] == "lexical-test/v1"
        assert chunk.metadata["ingest_run_id"] == "test-run"


def test_personal_data_never_reaches_the_store(chunks):
    store, _ = _persist(chunks)
    for chunk in store.get_all():
        lowered = chunk.text.lower()
        assert "ee-4419" not in lowered
        assert "priya" not in lowered
        assert "8821" not in lowered


def test_empty_upsert_leaves_the_store_empty():
    store, persisted = _persist([])
    assert persisted == []
    assert store.count() == 0


def test_chroma_upsert_is_idempotent_and_filterable(chunks, tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma", "policy_chunks")
    _persist(chunks, store)
    _persist(chunks, store)
    assert store.count() == 44
    live = store.get_all(where={"authority_rank": {"$gte": 2}})
    assert len(live) == 44
    current = store.get_all(where={"status": "current"})
    ids = {chunk.chunk_id for chunk in current}
    assert "ap-us-0001-v2.0#AP-5.1" in ids
    assert "ap-us-0001-v1.0#AP-5.1" not in ids


def test_upsert_logs_counts_not_payload(chunks, capsys, parse_log_lines):
    configure_logging()
    _persist(chunks, run_id="log-idx")
    stderr = capsys.readouterr().err
    assert "priya" not in stderr.lower()
    assert "EE-4419" not in stderr
    events = {row["event"]: row for row in parse_log_lines(stderr)}
    assert events["ingest.upsert"]["chunk_count"] == 44
    assert events["ingest.upsert"]["store_count"] == 44
    assert events["ingest.upsert"]["embedding_model"] == "lexical-test/v1"
