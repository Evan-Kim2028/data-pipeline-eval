from __future__ import annotations


class FirstLoadState:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.seen: set[str] = set()

    def absorb(self, incoming: list[dict]) -> list[dict]:
        for row in incoming:
            key = row["event_id"]
            if key in self.seen:
                continue
            self.seen.add(key)
            self.rows.append(row)
        return list(self.rows)


def merge_always_unique(existing: list[dict], incoming: list[dict], unique_fn) -> list[dict]:
    return unique_fn(list(existing) + list(incoming))


def merge_incoming(existing: list[dict], incoming: list[dict], unique_fn) -> list[dict]:
    if not existing:
        return FirstLoadState().absorb(incoming)
    return unique_fn(list(existing) + list(incoming))
