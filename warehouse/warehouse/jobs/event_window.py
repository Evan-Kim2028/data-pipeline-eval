from __future__ import annotations

from warehouse.event_time import in_event_window


def facts_in_window(
    events: list[dict],
    start: str,
    end: str,
    closed_processing_at: str,
) -> list[dict]:
    return in_event_window(events, start, end, closed_processing_at)
