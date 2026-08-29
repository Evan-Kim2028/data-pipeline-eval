from __future__ import annotations

from datetime import timedelta

from app.clock import utc_today


def lookback_since(days: int):
    return utc_today() - timedelta(days=max(days, 1))
