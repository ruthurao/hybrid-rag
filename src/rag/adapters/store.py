from __future__ import annotations

from pathlib import Path
from typing import Sequence

from src.rag.models import Chunk, Hit


def _matches(metadata: dict, where: dict | None) -> bool:
    if not where:
        return True
    return all(str(metadata.get(key)) == str(value) for key, value in where.items())


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}

    def upsert(self, chunks: Sequence[Chunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def query(
        self,
        vector: Sequence[float],
        k: int,
        where: dict | None = None,
    ) -> list[Hit]:
        scored: list[Hit] = []
        for chunk in self._chunks.values():
            if not _matches(chunk.metadata, where):
                continue
            if not chunk.embedding:
                continue
            scored.append(
                Hit(chunk=chunk, score=_cosine(vector, chunk.embedding), source="vector")
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    def get_all(self, where: dict | None = None) -> list[Chunk]:
        return [c for c in self._chunks.values() if _matches(c.metadata, where)]

    def count(self) -> int:
        return len(self._chunks)


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        import chromadb

        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: Sequence[Chunk]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[_chroma_meta(c.metadata) for c in chunks],
        )

    def query(
        self,
        vector: Sequence[float],
        k: int,
        where: dict | None = None,
    ) -> list[Hit]:
        kwargs: dict = {
            "query_embeddings": [list(vector)],
            "n_results": max(k, 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        result = self._collection.query(**kwargs)
        hits: list[Hit] = []
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
            chunk = Chunk(chunk_id=chunk_id, text=doc or "", metadata=dict(meta or {}))
            hits.append(Hit(chunk=chunk, score=1.0 - float(dist), source="vector"))
        return hits[:k]

    def get_all(self, where: dict | None = None) -> list[Chunk]:
        kwargs: dict = {"include": ["documents", "metadatas"]}
        if where:
            kwargs["where"] = where
        result = self._collection.get(**kwargs)
        return [
            Chunk(chunk_id=chunk_id, text=doc or "", metadata=dict(meta or {}))
            for chunk_id, doc, meta in zip(
                result.get("ids") or [],
                result.get("documents") or [],
                result.get("metadatas") or [],
            )
        ]

    def count(self) -> int:
        return self._collection.count()


def _chroma_meta(metadata: dict) -> dict:
    clean: dict = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        elif value is None:
            clean[key] = ""
        else:
            clean[key] = str(value)
    return clean
