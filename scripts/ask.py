from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.embedder import MiniLMEmbeddingAdapter  # noqa: E402
from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.config import default_settings  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402
from src.rag.query import SCOPE_COMPARE, SCOPE_DIAGNOSIS, SCOPE_LIVE, ask  # noqa: E402
from src.rag.rerank import CrossEncoderReranker  # noqa: E402

_SCOPES = (SCOPE_LIVE, SCOPE_DIAGNOSIS, SCOPE_COMPARE)


def main() -> None:
    configure_logging()
    scope, query = _parse_args(sys.argv[1:])
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
        scope=scope,
        reranker=CrossEncoderReranker(),
    )
    print(answer.text)
    print("Citations:")
    for cite in answer.citations:
        print(f"  {cite['doc_id']} {cite['version']} {cite['section']}")
    print("cache_hit:", answer.query_trace.cache_hit)


def _parse_args(argv: list[str]) -> tuple[str, str]:
    scope = SCOPE_LIVE
    args = list(argv)
    if args and args[0] == "--scope":
        if len(args) < 2:
            raise SystemExit(f"usage: ask.py [--scope {'|'.join(_SCOPES)}] QUERY")
        scope = args[1]
        args = args[2:]
    if scope not in _SCOPES:
        raise SystemExit(f"unknown scope {scope!r}; use {'|'.join(_SCOPES)}")
    query = " ".join(args) or "What is the invoice approval threshold?"
    return scope, query


def _ingest_run_id(store) -> str:
    chunks = store.get_all()
    if not chunks:
        raise SystemExit("index is empty; run scripts/ingest.py first")
    return str(chunks[0].metadata.get("ingest_run_id") or "unknown")


if __name__ == "__main__":
    main()
