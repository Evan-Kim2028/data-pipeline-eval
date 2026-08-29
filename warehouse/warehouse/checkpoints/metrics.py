from __future__ import annotations


def note(window: str, ok: bool) -> str:
    return f"{window}={'ok' if ok else 'fail'}"
