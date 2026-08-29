from __future__ import annotations

from datetime import timedelta

from warehouse.fixtures_synth import TODAY, events_history
from warehouse.jobs.event_window import facts_in_window


def test_late_fact_stays_in_event_time_window() -> None:
    events = events_history(42)
    start = (TODAY - timedelta(days=1)).isoformat()
    rows = facts_in_window(events, start, start, closed_processing_at=start)
    assert any(r["event_id"] == "ent-000-late" for r in rows)
    assert any(r["event_id"] == f"ent-000-{start}" for r in rows)


def test_on_time_facts_for_other_days_stay_out() -> None:
    events = events_history(42)
    start = (TODAY - timedelta(days=1)).isoformat()
    rows = facts_in_window(events, start, start, closed_processing_at=start)
    assert all(r["event_at"] == start for r in rows)
