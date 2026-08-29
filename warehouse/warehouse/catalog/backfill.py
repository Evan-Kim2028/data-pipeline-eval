from __future__ import annotations

from warehouse.catalog.publish import publish_row


def backfill_rows(table, rows: list[str]) -> None:
    for row in rows:
        publish_row(table, row)
