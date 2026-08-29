from __future__ import annotations

from datetime import date, timedelta

from warehouse.history.backfill import backfill
from warehouse.history.daily import publish_today
from warehouse.history.serve import current_as_of


def test_backfill_alone_does_not_advertise_oldest() -> None:
    today = date(2026, 8, 4)
    store: dict[str, str] = {}
    backfill(store, today, 10, payload_for=lambda d: f"p-{d.isoformat()}")
    oldest = today - timedelta(days=10)
    assert current_as_of(store) != oldest.isoformat()


def test_daily_publish_still_sets_latest() -> None:
    store: dict[str, str] = {}
    publish_today(store, date(2026, 8, 4), "today-mark")
    assert current_as_of(store) == "2026-08-04"
