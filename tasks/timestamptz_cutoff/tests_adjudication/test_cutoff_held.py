from __future__ import annotations

from datetime import date, datetime, timezone

from warehouse.sidecar.binder import bind_timestamptz
from warehouse.sidecar.cutoff import event_at_cutoff


def test_cutoff_is_aware_midnight_utc() -> None:
    bound = event_at_cutoff(date(2026, 1, 2))
    assert isinstance(bound, datetime)
    assert bound.tzinfo is not None
    assert bound.utcoffset() == timezone.utc.utcoffset(bound)
    assert bound.hour == 0
    assert bound.minute == 0
    assert bind_timestamptz(bound) == datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)


def test_year_month_and_leap_day_are_midnight_utc() -> None:
    for day in (date(2024, 1, 1), date(2024, 3, 1), date(2024, 2, 29)):
        bound = event_at_cutoff(day)
        assert bound == datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        assert bind_timestamptz(bound) == bound
