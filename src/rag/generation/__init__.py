"""Turn retrieved hits into an answer and citations."""

from src.rag.generation.generate import ExtractiveGenerator, generate

__all__ = ["ExtractiveGenerator", "generate"]
