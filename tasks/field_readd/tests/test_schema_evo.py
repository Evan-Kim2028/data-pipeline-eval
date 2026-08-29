from __future__ import annotations

from warehouse.jobs.schema_evo import drop_and_readd
from warehouse.schema_evo import ColumnStore


def test_readd_does_not_reuse_dropped_field_id() -> None:
    store = ColumnStore()
    store.add_field("note", "str")
    store.append_row({"note": "legacy"})
    drop_and_readd(store, "note", "int")
    store.append_row({"note": 7})
    col = store.read_column("note")
    assert "legacy" not in col
    assert 7 in col
