from __future__ import annotations

from datetime import date, timedelta

from warehouse.history.backfill import backfill
from warehouse.history.daily import publish_today
from warehouse.history.paths import day_key
from warehouse.history.serve import current_as_of


def test_backfill_does_not_move_latest_onto_the_oldest_day() -> None:
    today = date(2026, 8, 4)
    store: dict[str, str] = {}
    publish_today(store, today, "today-mark")
    n = backfill(store, today, 90, payload_for=lambda d: f"p-{d.isoformat()}")
    assert n == 90
    oldest = today - timedelta(days=90)
    assert current_as_of(store) == today.isoformat()
    assert current_as_of(store) != oldest.isoformat()
    assert day_key(oldest) in store
    assert day_key(today - timedelta(days=1)) in store
    assert store[day_key(today)] == "today-mark"
