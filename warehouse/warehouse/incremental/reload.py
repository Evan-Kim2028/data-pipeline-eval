from __future__ import annotations


def load_all_for_ids(events: list[dict], changed_ids: set[str]) -> list[dict]:
    return [row for row in events if row["entity_id"] in changed_ids]


def load_changed(events: list[dict], changed_ids: set[str], since: str) -> list[dict]:
    return [
        row
        for row in events
        if row["entity_id"] in changed_ids and row["event_at"] >= since
    ]
