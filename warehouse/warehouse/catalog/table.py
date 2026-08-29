from __future__ import annotations

from warehouse.errors import CommitConflict


class Table:
    def __init__(self) -> None:
        self.head = 1
        self.seen = 1
        self.payloads: list[str] = []
        self.refreshes = 0

    def refresh(self) -> None:
        self.refreshes += 1
        self.seen = self.head

    def commit(self, payload: str) -> None:
        if self.seen != self.head:
            raise CommitConflict(f"stale snapshot seen={self.seen} head={self.head}")
        self.head += 1
        self.seen = self.head
        self.payloads.append(payload)
