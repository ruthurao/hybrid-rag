from __future__ import annotations

from typing import Protocol, Sequence


class EmbeddingAdapter(Protocol):
    model_name: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return L2-normalized vectors, one per text."""
