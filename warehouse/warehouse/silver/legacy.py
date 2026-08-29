from __future__ import annotations

from warehouse.settings import INFER_SAMPLE


def infer_kind_legacy(rows: list[dict]) -> type:
    head = rows[: min(50, INFER_SAMPLE)]
    if head and all(str(r.get("listing_id", "")).isdigit() for r in head):
        return int
    return str
