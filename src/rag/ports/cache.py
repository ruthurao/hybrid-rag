from __future__ import annotations

from typing import Protocol

from src.rag.models import Answer


class AnswerCache(Protocol):
    def get(self, key: str) -> Answer | None:
        """Return a prior answer, or None on a miss."""

    def set(self, key: str, answer: Answer) -> None:
        """Store an answer. Callers must not write empty or failed answers."""
