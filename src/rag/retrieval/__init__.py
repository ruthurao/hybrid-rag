"""Hybrid retrieve, rerank, and the ask() entry point."""

from src.rag.retrieval.query import SCOPE_COMPARE, SCOPE_DIAGNOSIS, SCOPE_LIVE, ask

__all__ = ["SCOPE_COMPARE", "SCOPE_DIAGNOSIS", "SCOPE_LIVE", "ask"]
