from __future__ import annotations

from datetime import timedelta

from warehouse.time.clock import local_today


def lookback_since(days: int):
    return local_today() - timedelta(days=max(days, 1))
