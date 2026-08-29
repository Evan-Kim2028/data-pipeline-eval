from __future__ import annotations


def empty_ladder() -> list[dict]:
    return []


def ladder_from_rows(rows: list[dict]) -> list[dict]:
    if not rows:
        return empty_ladder()
    return sorted(rows, key=lambda r: (r.get("price") is None, r.get("price") or 0))
