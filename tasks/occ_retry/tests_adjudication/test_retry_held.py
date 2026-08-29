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


def test_retry_trace_is_commit_then_refresh() -> None:
    table = Table()
    table.head = 2
    table.seen = 1
    trace: list[str] = []
    orig_commit = table.commit
    orig_refresh = table.refresh

    def commit(payload: str) -> None:
        trace.append("commit")
        orig_commit(payload)

    def refresh() -> None:
        trace.append("refresh")
        orig_refresh()

    table.commit = commit  # type: ignore[method-assign]
    table.refresh = refresh  # type: ignore[method-assign]
    publish_row(table, "row-z")
    assert trace == ["commit", "refresh", "commit"]
