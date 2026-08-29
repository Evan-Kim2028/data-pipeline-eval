from __future__ import annotations

from datetime import date, timedelta


def default_as_of(today: date, lag_days: int = 1) -> date:
    return today - timedelta(days=lag_days)
