from __future__ import annotations

from datetime import timedelta

from warehouse.fixtures_synth import TODAY, changelog, events_history
from warehouse.incremental.reload import EventScan, load_changed
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


def test_scan_pushes_entity_and_time_before_collect() -> None:
    rows = [
        {"entity_id": "a", "event_at": "2020-01-01"},
        {"entity_id": "a", "event_at": "2026-01-01"},
        {"entity_id": "b", "event_at": "2026-01-01"},
    ]
    scan = EventScan(rows)
    out = scan.where_entity_in({"a"}).where_event_at_since("2026-01-01").collect()
    assert [name for name, _ in scan.predicates] == ["entity_in", "event_at_since"]
    assert out == [{"entity_id": "a", "event_at": "2026-01-01"}]
    assert scan.collected is True


def test_row_exactly_at_since_is_kept() -> None:
    since = "2026-01-01"
    events = [
        {"entity_id": "a", "event_at": since},
        {"entity_id": "a", "event_at": "2019-01-01"},
        {"entity_id": "b", "event_at": since},
    ]
    out = load_changed(events, {"a"}, since)
    assert out == [{"entity_id": "a", "event_at": since}]
