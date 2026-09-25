from __future__ import annotations

import json

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.llm import OllamaGenerator
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.generate import NO_COMPARE, NO_HIT, ExtractiveGenerator, generate
from src.rag.logging import configure_logging
from src.rag.models import Chunk, Hit
from src.rag.query import ask

QUERY = "What is the invoice approval threshold?"
META = {
    "doc_id": "ap-us-0001",
    "version": "v2.0",
    "section": "AP-5.1",
    "record_id": "ap-us-0001-v2.0",
    "status": "current",
    "authority": "policy",
    "authority_rank": 2,
}


def _hit(text: str = "An invoice of $10,000 requires approval.") -> Hit:
    return Hit(chunk=Chunk("ap-us-0001-v2.0#AP-5.1", text, dict(META)), score=1.0)


def _store() -> InMemoryVectorStore:
    store = InMemoryVectorStore()
    chunk = _hit().chunk
    embedder = LexicalEmbeddingAdapter()
    vector = embedder.embed([chunk.text])[0]
    store.upsert([
        Chunk(chunk.chunk_id, chunk.text, dict(chunk.metadata), embedding=vector)
    ])
    return store


class StubGenerator:
    model_name = "stub-llm"

    def __init__(self, text: str = "The threshold is $10,000.") -> None:
        self.text = text
        self.calls = 0
        self.compare = None

    def generate(self, query: str, hits: list[Hit], *, compare: bool):
        self.calls += 1
        self.compare = compare
        if not hits:
            return NO_HIT, []
        return self.text, [
            {field: META[field] for field in (
                "doc_id", "version", "section", "record_id", "status", "authority"
            )}
        ]


class BoomGenerator:
    model_name = "boom"

    def generate(self, query: str, hits: list[Hit], *, compare: bool):
        raise RuntimeError("api down")


def test_extractive_generator_matches_paste():
    hit = _hit()
    assert ExtractiveGenerator().generate(QUERY, [hit], compare=False) == generate([hit])
    assert ExtractiveGenerator().generate(QUERY, [], compare=True) == (NO_COMPARE, [])


def test_ask_uses_generator_text_and_caches_it():
    cache = InMemoryAnswerCache()
    stub = StubGenerator()
    first = ask(QUERY, LexicalEmbeddingAdapter(), _store(), "run", cache=cache, generator=stub)
    second = ask(QUERY, LexicalEmbeddingAdapter(), _store(), "run", cache=cache, generator=stub)
    assert first.text == "The threshold is $10,000."
    assert first.citations[0]["section"] == "AP-5.1"
    assert first.query_trace.cache_hit is False
    assert second.query_trace.cache_hit is True
    assert stub.calls == 1


def test_failed_generator_is_not_cached():
    cache = InMemoryAnswerCache()
    store = _store()
    with pytest.raises(RuntimeError, match="api down"):
        ask(QUERY, LexicalEmbeddingAdapter(), store, "run", cache=cache, generator=BoomGenerator())
    answer = ask(QUERY, LexicalEmbeddingAdapter(), store, "run", cache=cache)
    assert answer.query_trace.cache_hit is False
    assert "$10,000" in answer.text


def test_ollama_generator_sends_the_excerpt_and_cites_metadata():
    seen: dict = {}

    def complete(messages):
        seen["messages"] = messages
        return "The threshold is $10,000."

    text, citations = OllamaGenerator(complete=complete).generate(
        QUERY, [_hit()], compare=False
    )
    assert text == "The threshold is $10,000."
    assert "$10,000" in seen["messages"][1]["content"]
    assert "AP-5.1" in seen["messages"][1]["content"]
    assert citations == [
        {
            "doc_id": "ap-us-0001",
            "version": "v2.0",
            "section": "AP-5.1",
            "record_id": "ap-us-0001-v2.0",
            "status": "current",
            "authority": "policy",
        }
    ]


def test_ollama_generator_skips_the_call_when_nothing_was_retrieved():
    def complete(messages):
        raise AssertionError("ollama should not be called")

    text, citations = OllamaGenerator(complete=complete).generate(
        QUERY, [], compare=False
    )
    assert text == NO_HIT
    assert citations == []
    text, citations = OllamaGenerator(complete=complete).generate(
        QUERY, [], compare=True
    )
    assert text == NO_COMPARE


def test_compare_prompt_names_both_versions():
    seen: dict = {}

    def complete(messages):
        seen["system"] = messages[0]["content"]
        return "Current is $10,000. The replaced rule was $7,500."

    OllamaGenerator(complete=complete).generate(
        "What changed?", [_hit()], compare=True
    )
    assert "replaced" in seen["system"].lower()
    assert "current" in seen["system"].lower()


def test_empty_model_text_raises():
    gen = OllamaGenerator(complete=lambda messages: "  ")
    with pytest.raises(RuntimeError, match="empty answer"):
        gen.generate(QUERY, [_hit()], compare=False)


def test_ask_logs_the_generator_model(capsys):
    import structlog

    configure_logging()
    try:
        ask(
            QUERY,
            LexicalEmbeddingAdapter(),
            _store(),
            "run",
            cache=InMemoryAnswerCache(),
            generator=StubGenerator(),
            request_id="llm-1",
        )
        events = []
        for raw in capsys.readouterr().err.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        generate = next(row for row in events if row["event"] == "query.generate")
        assert generate["model"] == "stub-llm"
    finally:
        structlog.reset_defaults()
