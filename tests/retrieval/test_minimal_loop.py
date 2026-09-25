from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.retrieval.minimal_loop import QUERY, SENTENCE_A, SENTENCE_B, run_minimal_loop


def test_closer_sentence_wins():
    ranked = run_minimal_loop(
        embedder=LexicalEmbeddingAdapter(),
        store=InMemoryVectorStore(),
    )
    assert ranked[0] == SENTENCE_A
    assert SENTENCE_B in ranked
    assert QUERY


def test_minimal_loop_uses_injected_ports_only():
    store = InMemoryVectorStore()
    run_minimal_loop(embedder=LexicalEmbeddingAdapter(), store=store)
    assert store.count() == 2
