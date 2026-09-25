from __future__ import annotations

from pathlib import Path
from typing import Sequence

from src.rag.adapters.embedder import MiniLMEmbeddingAdapter
from src.rag.adapters.store import ChromaVectorStore
from src.rag.config import Settings, default_settings
from src.rag.ingestion.ingest import ingest_pdfs
from src.rag.logging import get_logger
from src.rag.models import Chunk, Record
from src.rag.ports.embedder import EmbeddingAdapter
from src.rag.ports.store import VectorStoreAdapter


def persist_chunks(
    chunks: Sequence[Chunk],
    embedder: EmbeddingAdapter,
    store: VectorStoreAdapter,
    ingest_run_id: str,
) -> list[Chunk]:
    """Embed chunks and upsert by chunk_id. Same ids overwrite; they do not grow."""
    log = get_logger(ingest_run_id=ingest_run_id)
    if not chunks:
        log.info("ingest.upsert", chunk_count=0, store_count=store.count())
        return []
    vectors = embedder.embed([chunk.text for chunk in chunks])
    ready = [
        Chunk(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            metadata={**chunk.metadata, "embedding_model": embedder.model_name},
            embedding=vector,
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    store.upsert(ready)
    log.info(
        "ingest.upsert",
        chunk_count=len(ready),
        store_count=store.count(),
        embedding_model=embedder.model_name,
    )
    return ready


def build_index(
    corpus_dir: Path | None = None,
    settings: Settings | None = None,
    embedder: EmbeddingAdapter | None = None,
    store: VectorStoreAdapter | None = None,
    ingest_run_id: str | None = None,
) -> tuple[str, list[Record], list[Chunk]]:
    """Parse, chunk, embed, and persist. Does not answer questions."""
    settings = settings or default_settings()
    embedder = embedder or MiniLMEmbeddingAdapter(settings.embedding_model)
    store = store or ChromaVectorStore(settings.chroma_dir, settings.collection_name)
    run_id, records, chunks = ingest_pdfs(
        corpus_dir or settings.corpus_dir,
        ingest_run_id=ingest_run_id,
        settings=settings,
    )
    persisted = persist_chunks(chunks, embedder, store, run_id)
    return run_id, records, persisted
