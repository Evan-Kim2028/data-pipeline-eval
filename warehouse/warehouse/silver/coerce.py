from __future__ import annotations

from warehouse.settings import ID_FIELD


def as_ids(rows: list[dict], kind: type) -> list[str]:
    out: list[str] = []
    for row in rows:
        value = row[ID_FIELD]
        if kind is int:
            value = int(value)
        out.append(str(value))
    return out
