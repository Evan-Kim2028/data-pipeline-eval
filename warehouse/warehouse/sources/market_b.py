from __future__ import annotations

from warehouse.settings import DEFAULT_CURRENCY, EVENT_COLUMNS

SOURCE = "market_b"


def normalize(row: dict) -> dict:
    out = {"source": SOURCE, "currency": row.get("currency", DEFAULT_CURRENCY)}
    for col in EVENT_COLUMNS:
        if col in row:
            out[col] = row[col]
    return out


def source_id() -> str:
    return SOURCE
