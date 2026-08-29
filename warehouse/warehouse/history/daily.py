from __future__ import annotations

from datetime import date

from warehouse.history.sidecar import write_latest, write_partition


def publish_today(store: dict[str, str], today: date, payload: str) -> None:
    write_partition(store, today, payload)
    write_latest(store, today, payload)
