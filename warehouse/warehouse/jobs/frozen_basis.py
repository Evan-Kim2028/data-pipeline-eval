from __future__ import annotations

from warehouse.incremental.basis import merge_incoming


def merge_first_load(incoming: list[dict], unique_fn) -> list[dict]:
    return merge_incoming([], incoming, unique_fn)
