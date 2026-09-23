from __future__ import annotations

from src.rag.logging import configure_logging, get_logger

REQUIRED_KEYS = {"timestamp", "level", "event"}


def test_logger_emits_required_keys(capsys, parse_log_lines):
    configure_logging()
    log = get_logger(ingest_run_id="run-1")
    log.info("ingest.start", pdf_count=4)

    events = parse_log_lines(capsys.readouterr().err)
    assert events, "expected at least one JSON log line on stderr"
    payload = events[-1]
    assert REQUIRED_KEYS <= payload.keys()
    assert payload["event"] == "ingest.start"
    assert payload["level"] == "info"
    assert payload["ingest_run_id"] == "run-1"
    assert payload["pdf_count"] == 4


def test_logger_does_not_emit_junk_text(capsys, parse_log_lines):
    configure_logging()
    log = get_logger(ingest_run_id="run-1")
    log.info("ingest.record", record_id="mec-us-0001-v1.0", junk_tagged=True)

    stderr = capsys.readouterr().err.lower()
    assert "priya" not in stderr
    assert "ee-4419" not in stderr
    assert "8821" not in stderr
    payload = parse_log_lines(stderr)[-1]
    assert payload["junk_tagged"] is True
    assert "junk_text" not in payload
