from __future__ import annotations


class Catalog:
    def __init__(self) -> None:
        self.tables: dict[str, dict] = {}
        self.tombstones: set[str] = set()

    def create(self, name: str) -> dict:
        if name in self.tombstones:
            raise RuntimeError(f"dropped:{name}")
        self.tables[name] = {}
        return self.tables[name]

    def drop(self, name: str) -> None:
        self.tables.pop(name, None)
        self.tombstones.add(name)

    def get_or_create(self, name: str) -> dict:
        if name in self.tables:
            return self.tables[name]
        self.tables[name] = {}
        self.tombstones.discard(name)
        return self.tables[name]
