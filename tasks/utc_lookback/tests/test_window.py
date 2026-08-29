from __future__ import annotations

from datetime import date, datetime, timezone

from warehouse.time.job import window_start
from warehouse.time.lookback import lookback_since


def test_lookback_uses_utc_date_not_local_calendar(monkeypatch) -> None:
    class FakeDate(date):
        @classmethod
        def today(cls) -> date:
            return date(2026, 8, 26)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            utc = datetime(2026, 8, 27, 2, 0, 0, tzinfo=timezone.utc)
            if tz is None:
                return datetime(2026, 8, 26, 22, 0, 0)
            return utc.astimezone(tz)

    monkeypatch.setattr("warehouse.time.clock.date", FakeDate)
    monkeypatch.setattr("warehouse.time.clock.datetime", FakeDatetime, raising=False)
    assert lookback_since(90) == date(2026, 5, 29)
    assert window_start(90) == date(2026, 5, 29)


def test_local_ahead_of_utc_still_uses_utc_date(monkeypatch) -> None:
    class FakeDate(date):
        @classmethod
        def today(cls) -> date:
            return date(2026, 8, 28)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            utc = datetime(2026, 8, 27, 22, 0, 0, tzinfo=timezone.utc)
            if tz is None:
                return datetime(2026, 8, 28, 2, 0, 0)
            return utc.astimezone(tz)

    monkeypatch.setattr("warehouse.time.clock.date", FakeDate)
    monkeypatch.setattr("warehouse.time.clock.datetime", FakeDatetime, raising=False)
    assert lookback_since(1) == date(2026, 8, 26)
    assert window_start(1) == lookback_since(1)


def test_nonpositive_days_normalize_to_one(monkeypatch) -> None:
    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr("warehouse.time.clock.datetime", FakeDatetime, raising=False)
    assert lookback_since(0) == date(2026, 8, 26)
    assert lookback_since(-3) == date(2026, 8, 26)
