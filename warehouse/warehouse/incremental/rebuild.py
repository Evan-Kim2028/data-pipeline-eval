from __future__ import annotations


def restart(staging: dict[str, int]) -> int:
    staging.clear()
    return 0


def next_chunk(staging: dict[str, int], last_ok: int | None) -> int:
    if last_ok is None:
        return 0
    staging["last_ok"] = last_ok
    return last_ok + 1
