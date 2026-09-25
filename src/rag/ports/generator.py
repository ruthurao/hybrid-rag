from __future__ import annotations

from typing import Protocol

from src.rag.models import Hit


class Generator(Protocol):
    model_name: str

    def generate(
        self, query: str, hits: list[Hit], *, compare: bool
    ) -> tuple[str, list[dict]]:
        """Answer from these hits. Citations come from hit metadata."""
