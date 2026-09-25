from __future__ import annotations

from src.rag.adapters.embedder import LexicalEmbeddingAdapter, MiniLMEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.models import Chunk
from src.rag.ports.embedder import EmbeddingAdapter
from src.rag.ports.store import VectorStoreAdapter

SENTENCE_A = "The finance manager approves large vendor invoices."
SENTENCE_B = "Cats sleep on warm sunny windowsills."
QUERY = "Who approves vendor invoices?"


def run_minimal_loop(
    embedder: EmbeddingAdapter | None = None,
    store: VectorStoreAdapter | None = None,
    use_minilm: bool = False,
) -> list[str]:
    """Embed two sentences, store them, retrieve by the question. Closer sentence wins."""
    if embedder is None:
        embedder = MiniLMEmbeddingAdapter() if use_minilm else LexicalEmbeddingAdapter()
    store = store or InMemoryVectorStore()
    sentences = [SENTENCE_A, SENTENCE_B]
    vectors = embedder.embed(sentences)
    store.upsert(
        [
            Chunk(chunk_id=f"s{i}", text=text, metadata={"label": text}, embedding=vector)
            for i, (text, vector) in enumerate(zip(sentences, vectors), start=1)
        ]
    )
    hits = store.query(embedder.embed([QUERY])[0], k=2)
    return [hit.chunk.text for hit in hits]
