"""Golden-set JSON and the eval run record.

Vector ids are the ANN list, before keyword fusion. Record ids are the
documents named on the answer's citations. A rubric miss fails the run.
A stress miss is stored and does not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.rag.eval.cases import EXTRA_CASES, RUBRIC_CASES, STRESS_CASES, EvalCase

GROUP_RUBRIC = "rubric"
GROUP_EXTRA = "extra"
GROUP_STRESS = "stress"


@dataclass(frozen=True)
class CaseScore:
    name: str
    group: str
    gold_chunk_ids: tuple[str, ...]
    gold_record_ids: tuple[str, ...]
    vector_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    gold_chunks: int
    chunks_found: int
    facts: int
    facts_found: int
    missing_chunks: tuple[str, ...]
    missing_records: tuple[str, ...]
    missing_facts: tuple[str, ...]
    entailment: tuple[float, ...]
    has_claims: bool
    tau_pass: bool
    leaked: tuple[str, ...]
    leaked_records: tuple[str, ...]
    missing_authority: tuple[tuple[str, str], ...]


def case_document(case: EvalCase) -> dict:
    return {
        "name": case.name,
        "query": case.query,
        "scope": case.scope,
        "must_chunk_ids": list(case.must_chunk_ids),
        "must_record_ids": list(case.must_record_ids),
        "must_not_record_ids": list(case.must_not_record_ids),
        "must_contain": list(case.must_contain),
        "must_not_contain": list(case.must_not_contain),
        "must_authority": [list(pair) for pair in case.must_authority],
        "must_entail": list(case.must_entail),
    }


def golden_document() -> dict:
    return {
        "rubric": [case_document(case) for case in RUBRIC_CASES],
        "extra": [case_document(case) for case in EXTRA_CASES],
        "stress": [case_document(case) for case in STRESS_CASES],
    }


def case_failed(row: CaseScore) -> bool:
    return bool(
        row.missing_chunks
        or row.missing_records
        or row.missing_facts
        or row.leaked
        or row.leaked_records
        or row.missing_authority
        or (row.has_claims and not row.tau_pass)
    )


def rubric_passed(rows: list[CaseScore]) -> bool:
    return not any(case_failed(row) for row in rows if row.group == GROUP_RUBRIC)


def record_document(rows: list[CaseScore], *, models: dict) -> dict:
    return {
        "models": models,
        "rubric_pass": rubric_passed(rows),
        "summary": _summary(rows),
        "cases": [_case_record(row) for row in rows],
    }


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n")


def expected_record_ids(row: CaseScore) -> tuple[str, ...]:
    if row.gold_record_ids:
        return row.gold_record_ids
    seen: list[str] = []
    for chunk_id in row.gold_chunk_ids:
        record_id = chunk_id.split("#", 1)[0]
        if record_id not in seen:
            seen.append(record_id)
    return tuple(seen)


def _case_record(row: CaseScore) -> dict:
    vector_found, vector_missing = _split(row.gold_chunk_ids, set(row.vector_ids))
    record_gold = expected_record_ids(row)
    record_found, record_missing = _split(record_gold, set(row.record_ids))
    return {
        "name": row.name,
        "group": row.group,
        "pass": not case_failed(row),
        "vector": {
            "retrieved": list(row.vector_ids),
            "gold": list(row.gold_chunk_ids),
            "found": vector_found,
            "missing": vector_missing,
        },
        "record": {
            "cited": list(row.record_ids),
            "gold": list(record_gold),
            "found": record_found,
            "missing": record_missing,
            "leaked": list(row.leaked_records),
        },
        "chunks_found": row.chunks_found,
        "gold_chunks": row.gold_chunks,
        "missing_chunks": list(row.missing_chunks),
        "facts_found": row.facts_found,
        "facts": row.facts,
        "missing_facts": list(row.missing_facts),
        "entailment": [round(probability, 4) for probability in row.entailment],
        "tau_pass": row.tau_pass,
        "leaked": list(row.leaked),
        "missing_authority": [list(pair) for pair in row.missing_authority],
    }


def _summary(rows: list[CaseScore]) -> dict:
    summary = {}
    for group in (GROUP_RUBRIC, GROUP_EXTRA, GROUP_STRESS):
        grouped = [row for row in rows if row.group == group]
        vector_gold = sum(len(row.gold_chunk_ids) for row in grouped)
        vector_found = sum(len(_split(row.gold_chunk_ids, set(row.vector_ids))[0]) for row in grouped)
        record_gold = sum(len(expected_record_ids(row)) for row in grouped)
        record_found = sum(
            len(_split(expected_record_ids(row), set(row.record_ids))[0]) for row in grouped
        )
        summary[group] = {
            "cases": len(grouped),
            "failed": sum(1 for row in grouped if case_failed(row)),
            "vector_found": vector_found,
            "vector_gold": vector_gold,
            "record_found": record_found,
            "record_gold": record_gold,
        }
    return summary


def _split(gold: tuple[str, ...], have: set[str]) -> tuple[list[str], list[str]]:
    found = [item for item in gold if item in have]
    missing = [item for item in gold if item not in have]
    return found, missing
