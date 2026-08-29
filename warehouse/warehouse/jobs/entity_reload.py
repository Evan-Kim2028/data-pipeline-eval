from __future__ import annotations

from warehouse.incremental.reload import load_changed


def changed_ids(changelog: list[dict], since: str) -> set[str]:
    return {row["entity_id"] for row in changelog if row["changed_at"] >= since}


def run(events: list[dict], changelog: list[dict], since: str) -> list[dict]:
    return load_changed(events, changed_ids(changelog, since), since)
