from src.rag.ports import (
    ChunkingStrategy,
    EmbeddingAdapter,
    Generator,
    ParserAdapter,
    VectorStoreAdapter,
)


def test_ports_are_importable():
    assert ParserAdapter.__name__ == "ParserAdapter"
    assert EmbeddingAdapter.__name__ == "EmbeddingAdapter"
    assert VectorStoreAdapter.__name__ == "VectorStoreAdapter"
    assert ChunkingStrategy.__name__ == "ChunkingStrategy"
    assert Generator.__name__ == "Generator"
