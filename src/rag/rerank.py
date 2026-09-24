from __future__ import annotations

from src.rag.models import Hit


class IdentityReranker:
    """Keeps fused order. Used in tests so pytest never downloads a model."""

    model_name = "identity"

    def rerank(self, query: str, hits: list[Hit], top_n: int) -> list[Hit]:
        return hits[:top_n]


class CrossEncoderReranker:
    """ms-marco MiniLM. Lazy-import; pair-scores query against each chunk."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def rerank(self, query: str, hits: list[Hit], top_n: int) -> list[Hit]:
        if not hits:
            return []
        model = self._load()
        pairs = [(query, hit.chunk.text) for hit in hits]
        scores = model.predict(pairs)
        rescored = [
            Hit(chunk=hit.chunk, score=float(score), source="rerank")
            for hit, score in zip(hits, scores)
        ]
        rescored.sort(key=lambda h: h.score, reverse=True)
        return rescored[:top_n]

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model
