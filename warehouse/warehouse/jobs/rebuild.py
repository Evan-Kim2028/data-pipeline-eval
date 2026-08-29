from __future__ import annotations

from warehouse.incremental.rebuild import next_chunk


def resume(staging: dict[str, int], last_ok: int | None) -> int:
    return next_chunk(staging, last_ok)
