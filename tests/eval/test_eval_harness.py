from __future__ import annotations

import pytest

from src.rag.adapters.cache import InMemoryAnswerCache
from src.rag.adapters.embedder import LexicalEmbeddingAdapter
from src.rag.adapters.store import InMemoryVectorStore
from src.rag.ingestion.index import persist_chunks
from src.rag.models import Answer
from src.rag.retrieval.query import SCOPE_DIAGNOSIS, SCOPE_LIVE, ask
from src.rag.eval.cases import CASES, RUBRIC_CASES, EvalCase


@pytest.fixture(scope="module")
def store(chunks):
    memory = InMemoryVectorStore()
    persist_chunks(chunks, LexicalEmbeddingAdapter(), memory, "test-run")
    return memory


def _run(store, case: EvalCase) -> Answer:
    return ask(
        case.query,
        LexicalEmbeddingAdapter(),
        store,
        "test-run",
        cache=InMemoryAnswerCache(),
        scope=case.scope,
    )


def test_rubric_set_has_eight_unique_questions():
    assert len(RUBRIC_CASES) == 8
    queries = [case.query for case in RUBRIC_CASES]
    assert len(set(queries)) == 8


def test_ask_cli_parses_diagnosis_scope():
    from scripts.ask import _parse_args

    scope, query = _parse_args(
        ["--scope", "diagnosis", "What invoice amount needs finance manager approval?"]
    )
    assert scope == SCOPE_DIAGNOSIS
    assert "invoice amount" in query
    assert _parse_args(["threshold?"])[0] == SCOPE_LIVE


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_case_has_gold_chunk_and_fact(case: EvalCase):
    assert case.must_chunk_ids, f"{case.name} has no gold chunk"
    assert case.must_contain or case.must_authority, f"{case.name} has no gold fact"


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_recall(store, case: EvalCase):
    answer = _run(store, case)
    retrieved = set(answer.query_trace.chunk_ids)
    missing = set(case.must_chunk_ids) - retrieved
    assert not missing, f"{case.name} missing chunks: {missing} have {retrieved}"


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_accuracy(store, case: EvalCase):
    answer = _run(store, case)
    records = {cite["record_id"] for cite in answer.citations}
    text = answer.text
    missing_records = set(case.must_record_ids) - records
    assert not missing_records, f"{case.name} missing records: {missing_records}"
    leaked = set(case.must_not_record_ids) & records
    assert not leaked, f"{case.name} leaked records: {leaked}"
    for needle in case.must_contain:
        assert needle in text, f"{case.name} missing {needle!r}"
    lowered = text.lower()
    for needle in case.must_not_contain:
        assert needle.lower() not in lowered, f"{case.name} leaked {needle!r}"
    cited = {(cite.get("section"), cite.get("authority")) for cite in answer.citations}
    for section, authority in case.must_authority:
        assert (section, authority) in cited, (
            f"{case.name} expected {section} as {authority}, have {cited}"
        )
