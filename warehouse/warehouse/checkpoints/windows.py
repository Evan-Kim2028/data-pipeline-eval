from __future__ import annotations


def upcoming(windows: list[str], last: str) -> list[str]:
    if not last:
        return list(windows)
    return [w for w in windows if w > last]
