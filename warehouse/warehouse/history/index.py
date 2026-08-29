from __future__ import annotations

from warehouse.history.paths import latest_key


def day_keys(store: dict[str, str]) -> list[str]:
    skip = {latest_key(), "latest_as_of"}
    return sorted(k for k in store if k not in skip)
