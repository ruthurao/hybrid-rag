from src.rag.ports import (
    ChunkingStrategy,
    EmbeddingAdapter,
    ParserAdapter,
    VectorStoreAdapter,
)


def test_ports_are_importable():
    assert ParserAdapter.__name__ == "ParserAdapter"
    assert EmbeddingAdapter.__name__ == "EmbeddingAdapter"
    assert VectorStoreAdapter.__name__ == "VectorStoreAdapter"
    assert ChunkingStrategy.__name__ == "ChunkingStrategy"
