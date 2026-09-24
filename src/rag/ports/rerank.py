from __future__ import annotations

from typing import Protocol

from src.rag.models import Hit


class Reranker(Protocol):
    model_name: str

    def rerank(self, query: str, hits: list[Hit], top_n: int) -> list[Hit]:
        """Rescore hits against the query and return at most top_n."""
