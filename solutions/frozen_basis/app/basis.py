from __future__ import annotations


def merge_always_unique(existing: list[dict], incoming: list[dict], unique_fn) -> list[dict]:
    return unique_fn(list(existing) + list(incoming))


def merge_incoming(existing: list[dict], incoming: list[dict], unique_fn) -> list[dict]:
    if not existing:
        return list(incoming)
    return unique_fn(existing + incoming)
