from __future__ import annotations


class WindowState:
    def __init__(self, start: str, end: str, lateness: str | None) -> None:
        self.start = start
        self.end = end
        self.lateness = lateness
        self.facts: dict[str, dict] = {}

    def ingest(self, events: list[dict], closed_processing_at: str) -> list[dict]:
        for event in events:
            event_at = event["event_at"]
            if event_at < self.start or event_at > self.end:
                continue
            if self.lateness is not None and event["processing_at"] > self.lateness:
                continue
            self.facts[event["event_id"]] = event
        _ = closed_processing_at
        return list(self.facts.values())


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
    return WindowState(start, end, lateness=None).ingest(events, closed_processing_at)
