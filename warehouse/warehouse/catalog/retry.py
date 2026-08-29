from __future__ import annotations

from warehouse.errors import CommitConflict
from warehouse.settings import MAX_COMMIT_ATTEMPTS


def run_with_retry(table, payload: str, *, max_attempts: int = MAX_COMMIT_ATTEMPTS) -> None:
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
