from __future__ import annotations

from datetime import date, timedelta

from warehouse.history.sidecar import write_latest, write_partition


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
        payload = payload_for(as_of)
        write_partition(store, as_of, payload)
        write_latest(store, as_of, payload)
        written += 1
    return written
