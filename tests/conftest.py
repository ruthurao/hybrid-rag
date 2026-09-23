from __future__ import annotations

import json

import pytest


@pytest.fixture
def parse_log_lines():
    def _parse(stderr: str) -> list[dict]:
        lines = []
        for raw in stderr.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return lines

    return _parse
