from __future__ import annotations

from warehouse.settings import INFER_SAMPLE


def _looks_int(value: object) -> bool:
    return str(value).isdigit()


def infer_listing_id_kind(rows: list[dict], *, sample: int | None = None) -> type:
    n = INFER_SAMPLE if sample is None else sample
    head = rows[:n]
    if head and all(_looks_int(r.get("listing_id")) for r in head):
        return int
    return str


def infer_default(rows: list[dict]) -> type:
    return infer_listing_id_kind(rows)
