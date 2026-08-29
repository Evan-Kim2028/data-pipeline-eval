from __future__ import annotations


def summarize(ids: list[str]) -> str:
    n_digit = sum(1 for i in ids if i.isdigit())
    return f"rows={len(ids)} numeric_looking={n_digit} uuid_looking={len(ids) - n_digit}"
