from __future__ import annotations


class MemorySink:
    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, label: str) -> None:
        self.writes.append(label)
