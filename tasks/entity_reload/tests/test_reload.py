from __future__ import annotations

from datetime import timedelta

from warehouse.fixtures_synth import TODAY, changelog, events_history
from warehouse.jobs.entity_reload import run


def test_changed_entity_reload_honors_since() -> None:
    events = events_history(42)
    since = (TODAY - timedelta(days=7)).isoformat()
    rows = run(events, changelog(42), since)
    assert rows
    assert all(r["entity_id"] == "ent-000" for r in rows)
    assert all(r["event_at"] >= since for r in rows)
    assert any(e["entity_id"] == "ent-000" and e["event_at"] < since for e in events)
    assert len(rows) < 20
