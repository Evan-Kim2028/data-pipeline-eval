from __future__ import annotations


def fmt(op: str, attempt: int, err: str) -> str:
    return f"COMMIT_RETRY op={op} attempt={attempt} error={err}"
