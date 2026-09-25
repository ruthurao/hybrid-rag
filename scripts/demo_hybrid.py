from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.embedder import MiniLMEmbeddingAdapter  # noqa: E402
from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.config import default_settings  # noqa: E402
from src.rag.retrieval.hybrid import hybrid_retrieve  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402
from src.rag.retrieval.query import SCOPE_LIVE, retrieve_filter  # noqa: E402


QUERY = "What is account code 6100 used for at travel close?"


def main() -> None:
    configure_logging()
    settings = default_settings(ROOT)
    store = ChromaVectorStore(settings.chroma_dir, settings.collection_name)
    if store.count() == 0:
        raise SystemExit("index is empty; run scripts/ingest.py first")
    embedder = MiniLMEmbeddingAdapter(settings.embedding_model)
    where = retrieve_filter(SCOPE_LIVE, settings)
    vector_hits, keyword_hits, fused = hybrid_retrieve(
        QUERY, embedder.embed([QUERY])[0], store, where, settings
    )
    print("Query:", QUERY)
    print()
    _dump("VECTOR ONLY", vector_hits)
    _dump("KEYWORD", keyword_hits)
    _dump("RRF FUSED", fused)
    table = "mec-us-0001-v1.0#MEC-5.1"
    travel = "mec-us-0001-v1.0#MEC-8.2"
    print()
    print("table chunk:", table)
    print("travel chunk:", travel)
    print("vector winner:", vector_hits[0].chunk.chunk_id if vector_hits else None)
    print("rrf winner:", fused[0].chunk.chunk_id if fused else None)
    print("rrf promoted the table:", fused and fused[0].chunk.chunk_id == table)


def _dump(title: str, hits) -> None:
    print(title)
    for i, hit in enumerate(hits[:5], start=1):
        mark = " << 6100" if "6100" in hit.chunk.text else ""
        print(f"  {i}. {hit.chunk.chunk_id}  {hit.score:.4f}{mark}")


if __name__ == "__main__":
    main()
