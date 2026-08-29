from __future__ import annotations

from datetime import timedelta

from warehouse.event_time import WindowState
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


def test_window_state_upserts_by_event_id_and_keeps_inclusive_bounds() -> None:
    state = WindowState("2026-01-02", "2026-01-02", lateness=None)
    first = state.ingest(
        [
            {"event_id": "e1", "event_at": "2026-01-02", "processing_at": "2026-01-02", "n": 1},
            {"event_id": "out", "event_at": "2026-01-01", "processing_at": "2026-01-02", "n": 0},
        ],
        closed_processing_at="2026-01-02",
    )
    second = state.ingest(
        [{"event_id": "e1", "event_at": "2026-01-02", "processing_at": "2026-01-03", "n": 2}],
        closed_processing_at="2026-01-02",
    )
    assert [r["event_id"] for r in first] == ["e1"]
    assert second[0]["n"] == 2


def test_lateness_policy_excludes_overdue_events() -> None:
    state = WindowState("2026-01-02", "2026-01-02", lateness="2026-01-03")
    rows = state.ingest(
        [
            {"event_id": "ok", "event_at": "2026-01-02", "processing_at": "2026-01-03"},
            {"event_id": "late", "event_at": "2026-01-02", "processing_at": "2026-01-04"},
        ],
        closed_processing_at="2026-01-02",
    )
    assert [r["event_id"] for r in rows] == ["ok"]
