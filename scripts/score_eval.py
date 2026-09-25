"""Print retrieval recall, answer key-info, and entailment tau-gate scores.

Same retrieve path as scripts/ask.py (Chroma, MiniLM, cross-encoder).
Generation is extractive. Entailment asks whether the retrieved policy text
supports each expected fact; a fact passes only when P(entailment) >= tau.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.cache import InMemoryAnswerCache  # noqa: E402
from src.rag.adapters.embedder import MiniLMEmbeddingAdapter  # noqa: E402
from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.config import default_settings  # noqa: E402
from src.rag.eval.entailment import EntailmentScorer, supporting_sentence, tau_gate  # noqa: E402
from src.rag.generation.generate import ExtractiveGenerator  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402
from src.rag.models import Chunk  # noqa: E402
from src.rag.retrieval.query import ask  # noqa: E402
from src.rag.retrieval.rerank import CrossEncoderReranker  # noqa: E402
from src.rag.eval.cases import CASES, RUBRIC_CASES, STRESS_CASES  # noqa: E402


@dataclass(frozen=True)
class CaseScore:
    name: str
    gold_chunks: int
    chunks_found: int
    facts: int
    facts_found: int
    missing_chunks: tuple[str, ...]
    missing_facts: tuple[str, ...]
    entailment: tuple[float, ...]
    has_claims: bool
    tau_pass: bool
    leaked: tuple[str, ...]
    missing_authority: tuple[tuple[str, str], ...]


def main() -> None:
    configure_logging()
    settings = default_settings(ROOT)
    store = ChromaVectorStore(settings.chroma_dir, settings.collection_name)
    if store.count() == 0:
        raise SystemExit("index is empty; run scripts/ingest.py first")
    embedder = MiniLMEmbeddingAdapter(settings.embedding_model)
    reranker = CrossEncoderReranker()
    generator = ExtractiveGenerator()
    entailment = EntailmentScorer(settings.entailment_model, settings.entailment_tau)
    chunks = store.get_all()
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    ingest_run_id = str(chunks[0].metadata.get("ingest_run_id") or "unknown")

    rows = [
        _score(case, embedder, store, reranker, generator, entailment, by_id, ingest_run_id, settings)
        for case in CASES + STRESS_CASES
    ]
    by_name = {row.name: row for row in rows}
    base = [by_name[case.name] for case in CASES]
    stress = [by_name[case.name] for case in STRESS_CASES]
    print(f"embedder: {embedder.model_name}")
    print(f"reranker: {reranker.model_name}")
    print(f"generator: {generator.model_name}")
    print(f"entailment: {entailment.model_name}")
    print(f"tau: {entailment.tau:.2f} ({_pct_float(entailment.tau)})")
    print()
    _report("Base", base, rubric=True)
    print()
    _report("Stress", stress, rubric=False)
    print()
    _misses(stress)


def _score(case, embedder, store, reranker, generator, entailment, by_id, ingest_run_id, settings) -> CaseScore:
    answer = ask(
        case.query,
        embedder,
        store,
        ingest_run_id,
        cache=InMemoryAnswerCache(),
        settings=settings,
        scope=case.scope,
        reranker=reranker,
        generator=generator,
    )
    retrieved = set(answer.query_trace.chunk_ids)
    missing_chunks = tuple(chunk_id for chunk_id in case.must_chunk_ids if chunk_id not in retrieved)
    missing_facts = tuple(fact for fact in case.must_contain if not _has(answer.text, fact))
    pairs = [
        (_fact_premise(fact, case.must_chunk_ids, retrieved, by_id), claim)
        for fact, claim in zip(case.must_contain, case.must_entail)
    ]
    probabilities = tuple(entailment.score_pairs(pairs))
    lowered = _flat(answer.text).lower()
    leaked = tuple(needle for needle in case.must_not_contain if _flat(needle).lower() in lowered)
    cited = {(cite.get("section"), cite.get("authority")) for cite in answer.citations}
    missing_authority = tuple(pair for pair in case.must_authority if pair not in cited)
    records = {cite["record_id"] for cite in answer.citations}
    missing_records = tuple(record_id for record_id in case.must_record_ids if record_id not in records)
    leaked_records = tuple(record_id for record_id in case.must_not_record_ids if record_id in records)
    return CaseScore(
        name=case.name,
        gold_chunks=len(case.must_chunk_ids),
        chunks_found=len(case.must_chunk_ids) - len(missing_chunks),
        facts=len(case.must_contain),
        facts_found=len(case.must_contain) - len(missing_facts),
        missing_chunks=missing_chunks + missing_records,
        missing_facts=missing_facts,
        entailment=probabilities,
        has_claims=bool(case.must_entail),
        tau_pass=(not case.must_entail) or tau_gate(list(probabilities), entailment.tau),
        leaked=leaked + leaked_records,
        missing_authority=missing_authority,
    )


def _fact_premise(fact: str, gold_ids: tuple[str, ...], retrieved: set[str], by_id: dict[str, Chunk]) -> str:
    for chunk_id in gold_ids:
        chunk = by_id.get(chunk_id)
        if chunk is None or chunk_id not in retrieved or not _has(chunk.text, fact):
            continue
        return supporting_sentence(chunk.text, _flat(fact))
    return ""


def _report(title: str, rows: list[CaseScore], *, rubric: bool) -> None:
    recall_rows = [row for row in rows if row.gold_chunks]
    fact_rows = [row for row in rows if row.facts]
    claim_rows = [row for row in rows if row.has_claims]
    gold = sum(row.gold_chunks for row in recall_rows)
    found = sum(row.chunks_found for row in recall_rows)
    facts = sum(row.facts for row in fact_rows)
    facts_found = sum(row.facts_found for row in fact_rows)
    full_recall = sum(1 for row in recall_rows if row.chunks_found == row.gold_chunks)
    full_facts = sum(1 for row in fact_rows if row.facts_found == row.facts)
    fact_probs = [probability for row in claim_rows for probability in row.entailment]
    mean_entailment = sum(fact_probs) / len(fact_probs) if fact_probs else 0.0
    gated = sum(1 for row in claim_rows if row.tau_pass)
    clean = sum(1 for row in rows if not row.leaked and not row.missing_authority)
    print(f"{title}: {len(rows)} cases")
    print(f"  retrieval recall: {found}/{gold} = {_pct(found, gold)}  ({full_recall}/{len(recall_rows)} cases)")
    print(f"  answer key information: {facts_found}/{facts} = {_pct(facts_found, facts)}  ({full_facts}/{len(fact_rows)} cases)")
    print(f"  mean P(entailment): {_pct_float(mean_entailment)}")
    print(f"  tau gate: {gated}/{len(claim_rows)} = {_pct(gated, len(claim_rows))}")
    print(f"  no leak: {clean}/{len(rows)} = {_pct(clean, len(rows))}")
    if rubric:
        rubric_rows = [row for row in rows if row.name in {case.name for case in RUBRIC_CASES}]
        print(f"  rubric recall: {_sum(rubric_rows, 'chunks_found')}/{_sum(rubric_rows, 'gold_chunks')} = {_pct(_sum(rubric_rows, 'chunks_found'), _sum(rubric_rows, 'gold_chunks'))}")
        print(f"  rubric key information: {_sum(rubric_rows, 'facts_found')}/{_sum(rubric_rows, 'facts')} = {_pct(_sum(rubric_rows, 'facts_found'), _sum(rubric_rows, 'facts'))}")


def _misses(rows: list[CaseScore]) -> None:
    misses = [
        row for row in rows
        if row.missing_chunks or row.missing_facts or row.leaked or row.missing_authority or (row.has_claims and not row.tau_pass)
    ]
    if not misses:
        print("Stress misses: none")
        return
    print("Stress misses")
    for row in misses:
        print(f"  {row.name}")
        if row.missing_chunks:
            print(f"    chunks: {', '.join(row.missing_chunks)}")
        if row.missing_facts:
            print(f"    facts: {', '.join(row.missing_facts)}")
        if row.leaked:
            print(f"    leaked: {', '.join(row.leaked)}")
        if row.missing_authority:
            print(f"    authority: {', '.join(f'{section}/{level}' for section, level in row.missing_authority)}")
        if row.has_claims and not row.tau_pass:
            shown = ", ".join(f"{probability:.0%}" for probability in row.entailment)
            print(f"    entailment below tau: {shown}")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _has(haystack: str, needle: str) -> bool:
    return _flat(needle) in _flat(haystack)


def _sum(rows: list[CaseScore], field: str) -> int:
    return sum(getattr(row, field) for row in rows)


def _pct(found: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{100 * found / total:.0f}%"


def _pct_float(value: float) -> str:
    return f"{100 * value:.0f}%"


if __name__ == "__main__":
    main()
