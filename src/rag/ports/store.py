from __future__ import annotations

from typing import Protocol, Sequence

from src.rag.models import Chunk, Hit


class VectorStoreAdapter(Protocol):
    def upsert(self, chunks: Sequence[Chunk]) -> None: ...

    def query(
        self,
        vector: Sequence[float],
        k: int,
        where: dict | None = None,
    ) -> list[Hit]: ...

    def get_all(self, where: dict | None = None) -> list[Chunk]: ...

    def count(self) -> int: ...
