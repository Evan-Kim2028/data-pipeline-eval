from __future__ import annotations


class FirstLoadState:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.seen: set[str] = set()

    def absorb(self, incoming: list[dict]) -> list[dict]:
        return list(incoming)


def merge_always_unique(existing: list[dict], incoming: list[dict], unique_fn) -> list[dict]:
    return unique_fn(list(existing) + list(incoming))


def merge_incoming(existing: list[dict], incoming: list[dict], unique_fn) -> list[dict]:
    return unique_fn(list(existing) + list(incoming))
