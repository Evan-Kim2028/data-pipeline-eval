from __future__ import annotations

from collections import Counter

_COUNTS: Counter[str] = Counter()


def inc(name: str, n: int = 1) -> None:
    _COUNTS[name] += n


def snapshot() -> dict[str, int]:
    return dict(_COUNTS)
