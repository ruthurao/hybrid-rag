from __future__ import annotations

from src.rag.models import Answer


class InMemoryAnswerCache:
    def __init__(self) -> None:
        self._answers: dict[str, Answer] = {}

    def get(self, key: str) -> Answer | None:
        return self._answers.get(key)

    def set(self, key: str, answer: Answer) -> None:
        self._answers[key] = answer
