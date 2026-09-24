from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.embedder import MiniLMEmbeddingAdapter  # noqa: E402
from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.config import default_settings  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402
from src.rag.query import ask  # noqa: E402
from src.rag.rerank import CrossEncoderReranker  # noqa: E402


def main() -> None:
    configure_logging()
    query = " ".join(sys.argv[1:]) or "What is the invoice approval threshold?"
    settings = default_settings(ROOT)
    store = ChromaVectorStore(settings.chroma_dir, settings.collection_name)
    embedder = MiniLMEmbeddingAdapter(settings.embedding_model)
    ingest_run_id = _ingest_run_id(store)
    answer = ask(
        query,
        embedder,
        store,
        ingest_run_id,
        settings=settings,
        reranker=CrossEncoderReranker(),
    )
    print(answer.text)
    print("Citations:")
    for cite in answer.citations:
        print(f"  {cite['doc_id']} {cite['version']} {cite['section']}")
    print("cache_hit:", answer.query_trace.cache_hit)


def _ingest_run_id(store) -> str:
    chunks = store.get_all()
    if not chunks:
        raise SystemExit("index is empty; run scripts/ingest.py first")
    return str(chunks[0].metadata.get("ingest_run_id") or "unknown")


if __name__ == "__main__":
    main()
