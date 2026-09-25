from __future__ import annotations

import json
from pathlib import Path

from src.rag.eval.record import (
    GROUP_RUBRIC,
    GROUP_STRESS,
    CaseScore,
    golden_document,
    record_document,
    rubric_passed,
    write_json,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "eval" / "golden.json"


def _row(name: str, group: str = GROUP_RUBRIC, **overrides) -> CaseScore:
    fields = dict(
        name=name,
        group=group,
        gold_chunk_ids=("ap-us-0001-v2.0#AP-5.1",),
        gold_record_ids=("ap-us-0001-v2.0",),
        vector_ids=("ap-us-0001-v2.0#AP-5.1",),
        record_ids=("ap-us-0001-v2.0",),
        gold_chunks=1,
        chunks_found=1,
        facts=1,
        facts_found=1,
        missing_chunks=(),
        missing_records=(),
        missing_facts=(),
        entailment=(0.9,),
        has_claims=True,
        tau_pass=True,
        leaked=(),
        leaked_records=(),
        missing_authority=(),
    )
    fields.update(overrides)
    return CaseScore(**fields)


def test_output_flag_sets_the_record_path():
    from scripts.score_eval import RECORD_PATH, _parse_args

    assert _parse_args([]).output == RECORD_PATH
    assert _parse_args(["--output", "eval/record.json"]).output == Path("eval/record.json")


def test_golden_file_matches_the_labeled_cases():
    assert json.loads(GOLDEN.read_text()) == golden_document()


def test_record_keeps_vector_hits_and_cited_records(tmp_path):
    row = _row(
        "live_approval_is_current_v2",
        vector_ids=("mec-us-0001-v1.0#MEC-8.2", "ap-us-0001-v2.0#AP-5.1"),
        record_ids=("ap-us-0001-v2.0",),
    )
    path = tmp_path / "record.json"
    document = record_document([row], models={"embedder": "minilm"})
    write_json(path, document)
    saved = json.loads(path.read_text())
    case = saved["cases"][0]
    assert case["vector"]["retrieved"][0] == "mec-us-0001-v1.0#MEC-8.2"
    assert case["vector"]["found"] == ["ap-us-0001-v2.0#AP-5.1"]
    assert case["record"]["cited"] == ["ap-us-0001-v2.0"]
    assert case["record"]["found"] == ["ap-us-0001-v2.0"]
    assert saved["rubric_pass"] is True


def test_rubric_miss_fails_and_names_the_case():
    miss = _row("live_lock_timing", missing_chunks=("mec-us-0001-v1.0#MEC-3.2",), chunks_found=0)
    document = record_document([miss], models={})
    assert rubric_passed([miss]) is False
    assert document["rubric_pass"] is False
    assert document["cases"][0]["name"] == "live_lock_timing"
    assert document["cases"][0]["pass"] is False


def test_stress_miss_is_recorded_and_does_not_fail_the_rubric():
    stress = _row(
        "stress_ten_thousand_paraphrase",
        GROUP_STRESS,
        missing_chunks=("ap-us-0001-v2.0#AP-5.1",),
        chunks_found=0,
    )
    document = record_document([stress], models={})
    assert rubric_passed([stress]) is True
    assert document["rubric_pass"] is True
    assert document["summary"]["stress"]["failed"] == 1
    assert document["cases"][0]["vector"]["retrieved"]
