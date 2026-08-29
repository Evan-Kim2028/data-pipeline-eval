from __future__ import annotations


def drop_frac(dropped: int, total: int) -> float:
    return dropped / max(total, 1)


def fail_closed(dropped: int, total: int, max_frac: float = 0.05) -> bool:
    return drop_frac(dropped, total) > max_frac
