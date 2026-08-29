from __future__ import annotations

from warehouse.schema_evo import ColumnStore


def test_two_readds_get_new_ids() -> None:
    store = ColumnStore()
    first = store.add_field("note", "str")
    store.drop_field("note")
    second = store.readd_field("note", "int")
    store.drop_field("note")
    third = store.readd_field("note", "int")
    assert second != first
    assert third != second
    assert third != first
