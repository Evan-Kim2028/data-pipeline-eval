from __future__ import annotations

from warehouse.history.paths import latest_key


def current_as_of(store: dict[str, str]) -> str | None:
    return store.get("latest_as_of")


def current_payload(store: dict[str, str]) -> str | None:
    return store.get(latest_key())
