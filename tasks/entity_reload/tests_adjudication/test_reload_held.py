from __future__ import annotations

from datetime import timedelta

from warehouse.fixtures_synth import TODAY, events_history
from warehouse.jobs.entity_reload import run


def test_unchanged_entity_is_not_reloaded() -> None:
    events = events_history(42)
    since = (TODAY - timedelta(days=7)).isoformat()
    changelog = [{"entity_id": "ent-002", "changed_at": (TODAY - timedelta(days=1)).isoformat()}]
    rows = run(events, changelog, since)
    assert rows
    assert all(r["entity_id"] == "ent-002" for r in rows)
    assert all(r["event_at"] >= since for r in rows)
