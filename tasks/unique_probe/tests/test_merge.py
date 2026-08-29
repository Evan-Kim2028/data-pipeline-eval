from __future__ import annotations

import pytest
from warehouse.gold.merge import merge_delta
from warehouse.gold.sink import MemorySink


class Scan:
    def __init__(self, n: int, calls: list[str] | None = None) -> None:
        self._n = n
        self.calls = calls if calls is not None else []

    def unique(self, **kwargs):
        self.calls.append("unique")
        raise MemoryError("unique() planned a full-delta unique")

    def sort(self, *args, **kwargs):
        self.calls.append("sort")
        return Scan(self._n, self.calls)

    def limit(self, n: int):
        self.calls.append("limit")
        return Scan(min(self._n, n), self.calls)

    def collect(self, **kwargs):
        self.calls.append("collect")
        return type("Rows", (), {"height": self._n})()


def test_nonempty_merge_does_not_unique_the_probe() -> None:
    scan = Scan(800)
    sink = MemorySink()
    assert merge_delta(scan, sink) == "merged"
    assert sink.writes == ["merged"]
    assert "unique" not in scan.calls


def test_empty_delta_skips_sink() -> None:
    scan = Scan(0)
    sink = MemorySink()
    assert merge_delta(scan, sink) == "empty"
    assert sink.writes == []


def test_unique_is_not_an_emptiness_check() -> None:
    scan = Scan(0)
    try:
        merge_delta(scan, MemorySink())
    except MemoryError:
        pytest.fail("unique() was planned on the empty probe")
