from __future__ import annotations

from warehouse.catalog.publish import publish_row
from warehouse.catalog.table import Table


def test_one_conflict_refreshes_once() -> None:
    table = Table()
    table.head = 2
    table.seen = 1
    publish_row(table, "row-x")
    assert table.payloads == ["row-x"]
    assert table.refreshes == 1
