from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path


def parse_rows(lines: Iterable[str]) -> list[dict]:
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def read_jsonl(path: Path) -> list[dict]:
    return parse_rows(path.read_text().splitlines())
