from __future__ import annotations

from datetime import date, datetime, timezone

from warehouse.time.lookback import lookback_since


def test_lookback_since_follows_utc_clock(monkeypatch) -> None:
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
    assert lookback_since(1) == date(2026, 8, 26)
