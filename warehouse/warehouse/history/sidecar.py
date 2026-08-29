from __future__ import annotations

from datetime import date

from warehouse.history.paths import day_key, latest_key


def write_partition(store: dict[str, str], as_of: date, payload: str) -> None:
    store[day_key(as_of)] = payload


def write_latest(store: dict[str, str], as_of: date, payload: str) -> None:
    store[latest_key()] = payload
    store["latest_as_of"] = as_of.isoformat()
