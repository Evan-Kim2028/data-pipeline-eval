from __future__ import annotations

from warehouse.schema_evo import ColumnStore


def drop_and_readd(store: ColumnStore, name: str, typ: str) -> int:
    store.drop_field(name)
    return store.readd_field(name, typ)
