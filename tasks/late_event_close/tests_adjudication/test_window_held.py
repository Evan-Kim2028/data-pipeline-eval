from __future__ import annotations

from datetime import timedelta

from warehouse.fixtures_synth import TODAY, events_history
from warehouse.jobs.event_window import facts_in_window


def test_closed_processing_at_does_not_drop_in_window_event() -> None:
    events = events_history(42)
    start = (TODAY - timedelta(days=1)).isoformat()
    closed = (TODAY - timedelta(days=2)).isoformat()
    rows = facts_in_window(events, start, start, closed_processing_at=closed)
    assert any(r["event_id"] == "ent-000-late" for r in rows)
