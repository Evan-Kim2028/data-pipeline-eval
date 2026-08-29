from __future__ import annotations

from warehouse.settings import INFER_SAMPLE


def _looks_int(value: object) -> bool:
    return str(value).isdigit()


def infer_listing_id_kind(rows: list[dict], *, sample: int | None = None) -> type:
    window = rows if sample is None else rows[:sample]
    if window and all(_looks_int(r.get("listing_id")) for r in window):
        return int
    return str


def infer_default(rows: list[dict]) -> type:
    return infer_listing_id_kind(rows, sample=None)
