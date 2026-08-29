from __future__ import annotations

from app.errors import CommitConflict

MAX_ATTEMPTS = 3


def run_with_retry(table, payload: str, *, max_attempts: int = MAX_ATTEMPTS) -> None:
    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            table.commit(payload)
            return
        except CommitConflict as exc:
            last = exc
            if attempt == max_attempts - 1:
                raise
            table.refresh()
    if last is not None:
        raise last
