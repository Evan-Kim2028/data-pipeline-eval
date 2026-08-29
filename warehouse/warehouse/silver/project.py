from __future__ import annotations

KEEP = ("listing_id", "source", "price", "currency", "sold_at", "fetched_at")


def project(raw: dict) -> dict:
    return {k: raw.get(k) for k in KEEP if k in raw}
