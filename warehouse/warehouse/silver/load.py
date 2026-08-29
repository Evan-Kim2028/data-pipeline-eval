from __future__ import annotations

from warehouse.ingest.jsonl import parse_rows
from warehouse.silver.coerce import as_ids
from warehouse.silver.project import project
from warehouse.silver.schema import infer_listing_id_kind


def load_listing_ids(lines: list[str]) -> list[str]:
    rows = [project(r) for r in parse_rows(lines)]
    if not rows:
        return []
    kind = infer_listing_id_kind(rows)
    return as_ids(rows, kind)
