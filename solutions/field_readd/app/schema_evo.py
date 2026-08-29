from __future__ import annotations


class ColumnStore:
    def __init__(self) -> None:
        self._next_id = 1
        self.fields: dict[str, tuple[int, str]] = {}
        self.rows: list[dict[int, object]] = []

    def add_field(self, name: str, typ: str) -> int:
        fid = self._next_id
        self._next_id += 1
        self.fields[name] = (fid, typ)
        return fid

    def drop_field(self, name: str) -> None:
        self.fields.pop(name, None)

    def readd_field(self, name: str, typ: str) -> int:
        return self.add_field(name, typ)

    def append_row(self, values: dict[str, object]) -> None:
        encoded: dict[int, object] = {}
        for name, value in values.items():
            fid, _typ = self.fields[name]
            encoded[fid] = value
        self.rows.append(encoded)

    def read_column(self, name: str) -> list[object]:
        fid, _typ = self.fields[name]
        return [row.get(fid) for row in self.rows]
