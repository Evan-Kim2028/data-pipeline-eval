from __future__ import annotations

from warehouse.catalog.retry import run_with_retry


def publish_row(table, payload: str) -> None:
    run_with_retry(table, payload)
