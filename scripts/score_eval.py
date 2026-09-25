"""Print retrieval recall, answer key-info, and entailment tau-gate scores.

Same retrieve path as scripts/ask.py (Chroma, MiniLM, cross-encoder).
Generation is extractive. Entailment asks whether the retrieved policy text
supports each expected fact; a fact passes only when P(entailment) >= tau.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.adapters.cache import InMemoryAnswerCache  # noqa: E402
from src.rag.adapters.embedder import MiniLMEmbeddingAdapter  # noqa: E402
from src.rag.adapters.store import ChromaVectorStore  # noqa: E402
from src.rag.config import default_settings  # noqa: E402
from src.rag.entailment import EntailmentScorer, supporting_sentence, tau_gate  # noqa: E402
from src.rag.generate import ExtractiveGenerator  # noqa: E402
from src.rag.logging import configure_logging  # noqa: E402
from src.rag.models import Chunk  # noqa: E402
from src.rag.query import ask  # noqa: E402
from src.rag.rerank import CrossEncoderReranker  # noqa: E402
from tests.eval_cases import CASES, RUBRIC_CASES  # noqa: E402


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
    tau_pass: bool


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
        for case in CASES
    ]
    _report(
        rows,
        embedder.model_name,
        reranker.model_name,
        generator.model_name,
        entailment.model_name,
        entailment.tau,
    )


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
    missing_facts = tuple(fact for fact in case.must_contain if fact not in answer.text)
    pairs = [
        (_fact_premise(fact, case.must_chunk_ids, retrieved, by_id), claim)
        for fact, claim in zip(case.must_contain, case.must_entail)
    ]
    probabilities = tuple(entailment.score_pairs(pairs))
    return CaseScore(
        name=case.name,
        gold_chunks=len(case.must_chunk_ids),
        chunks_found=len(case.must_chunk_ids) - len(missing_chunks),
        facts=len(case.must_contain),
        facts_found=len(case.must_contain) - len(missing_facts),
        missing_chunks=missing_chunks,
        missing_facts=missing_facts,
        entailment=probabilities,
        tau_pass=tau_gate(list(probabilities), entailment.tau),
    )


def _fact_premise(fact: str, gold_ids: tuple[str, ...], retrieved: set[str], by_id: dict[str, Chunk]) -> str:
    for chunk_id in gold_ids:
        chunk = by_id.get(chunk_id)
        if chunk is None or chunk_id not in retrieved or fact not in chunk.text:
            continue
        return supporting_sentence(chunk.text, fact)
    return ""


def _report(rows: list[CaseScore], embedder: str, reranker: str, generator: str, entailment_model: str, tau: float) -> None:
    gold = sum(row.gold_chunks for row in rows)
    found = sum(row.chunks_found for row in rows)
    facts = sum(row.facts for row in rows)
    facts_found = sum(row.facts_found for row in rows)
    full_recall = sum(1 for row in rows if row.chunks_found == row.gold_chunks and row.gold_chunks)
    full_facts = sum(1 for row in rows if row.facts and row.facts_found == row.facts)
    rubric_names = {case.name for case in RUBRIC_CASES}
    rubric = [row for row in rows if row.name in rubric_names]

    print(f"embedder: {embedder}")
    print(f"reranker: {reranker}")
    print(f"generator: {generator}")
    print(f"entailment: {entailment_model}")
    print(f"tau: {tau:.2f} ({_pct_float(tau)})")
    print(f"cases: {len(rows)} ({len(rubric)} rubric + {len(rows) - len(rubric)} extra)")
    print()
    print("Retrieval recall — gold chunk_id is in the chunks passed to generation")
    print(f"  micro: {found}/{gold} = {_pct(found, gold)}")
    print(f"  cases with every gold chunk: {full_recall}/{len(rows)} = {_pct(full_recall, len(rows))}")
    print(f"  rubric micro: {_sum(rubric, 'chunks_found')}/{_sum(rubric, 'gold_chunks')} = {_pct(_sum(rubric, 'chunks_found'), _sum(rubric, 'gold_chunks'))}")
    print()
    print("Answer key information — expected fact is in the generated text")
    print(f"  micro: {facts_found}/{facts} = {_pct(facts_found, facts)}")
    print(f"  cases with every fact: {full_facts}/{len(rows)} = {_pct(full_facts, len(rows))}")
    print(f"  rubric micro: {_sum(rubric, 'facts_found')}/{_sum(rubric, 'facts')} = {_pct(_sum(rubric, 'facts_found'), _sum(rubric, 'facts'))}")
    print()
    fact_probs = [probability for row in rows for probability in row.entailment]
    mean_entailment = sum(fact_probs) / len(fact_probs) if fact_probs else 0.0
    gated = sum(1 for row in rows if row.tau_pass)
    rubric_gated = sum(1 for row in rubric if row.tau_pass)
    print("Entailment — retrieved policy text entails each expected fact")
    print(f"  mean P(entailment): {_pct_float(mean_entailment)}")
    print(f"  tau gate: {gated}/{len(rows)} = {_pct(gated, len(rows))}")
    print(f"  rubric tau gate: {rubric_gated}/{len(rubric)} = {_pct(rubric_gated, len(rubric))}")
    print()
    misses = [row for row in rows if row.missing_chunks or row.missing_facts or not row.tau_pass]
    if not misses:
        print("Misses: none")
        return
    print("Misses")
    for row in misses:
        print(f"  {row.name}")
        if row.missing_chunks:
            print(f"    chunks: {', '.join(row.missing_chunks)}")
        if row.missing_facts:
            print(f"    facts: {', '.join(row.missing_facts)}")
        if not row.tau_pass:
            shown = ", ".join(f"{probability:.0%}" for probability in row.entailment)
            print(f"    entailment below tau: {shown}")


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
