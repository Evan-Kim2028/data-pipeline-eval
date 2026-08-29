from __future__ import annotations


def in_processing_window(
    events: list[dict],
    start: str,
    end: str,
    closed_processing_at: str,
) -> list[dict]:
    return [
        e
        for e in events
        if start <= e["event_at"] <= end and e["processing_at"] <= closed_processing_at
    ]


def in_event_window(
    events: list[dict],
    start: str,
    end: str,
    closed_processing_at: str,
) -> list[dict]:
    return [
        e
        for e in events
        if start <= e["event_at"] <= end and e["processing_at"] <= closed_processing_at
    ]
