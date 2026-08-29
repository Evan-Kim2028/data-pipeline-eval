from __future__ import annotations

from datetime import date, datetime, timezone


def event_at_cutoff(cutoff: date) -> object:
    return datetime(cutoff.year, cutoff.month, cutoff.day, tzinfo=timezone.utc)
