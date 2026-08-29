from __future__ import annotations


def _looks_int(value: object) -> bool:
    return str(value).isdigit()


def infer_listing_id_kind(rows: list[dict], *, sample: int | None = None) -> type:
    """Infer int vs str from the full batch.

    A head sample is not a schema. Marketplace B ids are UUIDs and
    show up after the numeric ones.
    """
    window = rows if sample is None else rows[:sample]
    if window and all(_looks_int(r.get("listing_id")) for r in window):
        return int
    return str
