from __future__ import annotations

import math
import re
from collections import Counter
from typing import Sequence


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _stable_index(token: str, dim: int) -> int:
    acc = 0
    for ch in token:
        acc = (acc * 31 + ord(ch)) & 0xFFFFFFFF
    return acc % dim


class LexicalEmbeddingAdapter:
    """Deterministic bag-of-words for tests. Same port as MiniLM."""

    def __init__(self, dim: int = 384, model_name: str = "lexical-test/v1") -> None:
        self.dim = dim
        self.model_name = model_name

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [_l2_normalize(self._vector(text)) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[a-z0-9$]+", text.lower())
        for token, n in Counter(tokens).items():
            vec[_stable_index(token, self.dim)] += float(n)
        return vec


class MiniLMEmbeddingAdapter:
    """all-MiniLM-L6-v2. Lazy-import so pytest can stay on the lexical adapter."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model
