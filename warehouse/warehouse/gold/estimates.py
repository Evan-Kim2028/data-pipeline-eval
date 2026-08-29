from __future__ import annotations

from warehouse.settings import EVENT_COLUMNS, LOOKBACK_DAYS


def required_columns() -> tuple[str, ...]:
    return tuple(EVENT_COLUMNS[:12])


def window_days() -> int:
    return LOOKBACK_DAYS
