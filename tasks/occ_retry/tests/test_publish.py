from __future__ import annotations

import pytest
from warehouse.catalog.backfill import backfill_rows
from warehouse.catalog.publish import publish_row
from warehouse.catalog.table import Table


def test_stale_handle_succeeds_after_refresh() -> None:
    table = Table()
    table.head = 2
    table.seen = 1
    publish_row(table, "row-1")
    assert table.payloads == ["row-1"]
    assert table.refreshes >= 1


def test_fresh_handle_does_not_refresh_first() -> None:
    table = Table()
    publish_row(table, "row-1")
    assert table.payloads == ["row-1"]
    assert table.refreshes == 0


def test_unrelated_errors_are_not_retries() -> None:
    class Boom(Table):
        def commit(self, payload: str) -> None:
            raise ValueError("not a conflict")

    with pytest.raises(ValueError, match="not a conflict"):
        publish_row(Boom(), "row-1")


def test_backfill_survives_one_conflict() -> None:
    table = Table()
    table.head = 2
    table.seen = 1
    backfill_rows(table, ["a", "b"])
    assert table.payloads == ["a", "b"]
