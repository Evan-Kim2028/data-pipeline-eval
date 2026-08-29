from __future__ import annotations


class EventScan:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = list(rows)
        self.predicates: list[tuple[str, object]] = []
        self.collected = False

    def where_entity_in(self, ids: set[str]) -> EventScan:
        wanted = set(ids)
        self.predicates.append(("entity_in", frozenset(wanted)))
        self._rows = [row for row in self._rows if row["entity_id"] in wanted]
        return self

    def where_event_at_since(self, since: str) -> EventScan:
        self.predicates.append(("event_at_since", since))
        return self

    def collect(self) -> list[dict]:
        self.collected = True
        return list(self._rows)


def load_all_for_ids(events: list[dict], changed_ids: set[str]) -> list[dict]:
    return EventScan(events).where_entity_in(changed_ids).collect()


def load_changed(events: list[dict], changed_ids: set[str], since: str) -> list[dict]:
    return EventScan(events).where_entity_in(changed_ids).collect()
