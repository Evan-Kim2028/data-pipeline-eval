from __future__ import annotations


class WindowState:
    def __init__(self, start: str, end: str, lateness: str) -> None:
        self.start = start
        self.end = end
        self.lateness = lateness
        self.facts: dict[str, dict] = {}

    def ingest(self, events: list[dict], closed_processing_at: str) -> list[dict]:
        for event in events:
            if start_bound(event, self.start, self.end) and event["processing_at"] <= closed_processing_at:
                self.facts[event["event_id"]] = event
        return list(self.facts.values())


def start_bound(event: dict, start: str, end: str) -> bool:
    return start <= event["event_at"] <= end


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
    return WindowState(start, end, lateness=end).ingest(events, closed_processing_at)
