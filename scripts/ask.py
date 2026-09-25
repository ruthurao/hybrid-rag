from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.embedder import MiniLMEmbeddingAdapter  # noqa: E402
from src.rag.adapters.llm import OllamaGenerator  # noqa: E402
from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.config import default_settings  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402
from src.rag.retrieval.query import SCOPE_COMPARE, SCOPE_DIAGNOSIS, SCOPE_LIVE, ask  # noqa: E402
from src.rag.retrieval.rerank import CrossEncoderReranker  # noqa: E402

LLM_PIPELINE_ID = "ollama-v1"

_SCOPES = (SCOPE_LIVE, SCOPE_DIAGNOSIS, SCOPE_COMPARE)


def main() -> None:
    configure_logging()
    scope, query = _parse_args(sys.argv[1:])
    generator = _generator()
    settings = replace(default_settings(ROOT), pipeline_id=LLM_PIPELINE_ID)
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
        generator=generator,
    )
    print(answer.text)
    print("Citations:")
    for cite in answer.citations:
        print(f"  {cite['doc_id']} {cite['version']} {cite['section']}")
    print("cache_hit:", answer.query_trace.cache_hit)


def _generator() -> OllamaGenerator:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
    if not host.startswith("http"):
        host = "http://" + host
    return OllamaGenerator(
        model_name=os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
        base_url=host,
    )


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
