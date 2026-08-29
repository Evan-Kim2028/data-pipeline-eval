from __future__ import annotations

from datetime import date, timedelta

from warehouse.history.sidecar import write_partition


def backfill(
    store: dict[str, str],
    today: date,
    days: int,
    *,
    payload_for,
) -> int:
    written = 0
    for offset in range(1, days + 1):
        as_of = today - timedelta(days=offset)
        write_partition(store, as_of, payload_for(as_of))
        written += 1
    return written
