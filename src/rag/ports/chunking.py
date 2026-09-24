from __future__ import annotations

from typing import Protocol

from src.rag.models import Chunk, Record


class ChunkingStrategy(Protocol):
    name: str

    def chunk(self, record: Record, ingest_run_id: str, embedding_model: str) -> list[Chunk]:
        """Split a record into section chunks.

        Blocks below the configured authority rank are dropped here, so
        untrusted content is never written to the store.
        """
