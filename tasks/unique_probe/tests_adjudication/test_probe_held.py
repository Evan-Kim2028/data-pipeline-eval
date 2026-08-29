from __future__ import annotations

from warehouse.gold.merge import merge_delta
from warehouse.gold.sink import MemorySink


class Scan:
    def __init__(self, n: int) -> None:
        self._n = n
        self.calls: list[str] = []

    def unique(self, **kwargs):
        self.calls.append("unique")
        raise MemoryError("unique() planned a full-delta unique")

    def limit(self, n: int):
        self.calls.append("limit")
        return Scan(min(self._n, n))

    def collect(self, **kwargs):
        self.calls.append("collect")
        return type("Rows", (), {"height": self._n})()


def test_streaming_probe_does_not_unique(monkeypatch) -> None:
    monkeypatch.setattr("warehouse.gold.probe.STREAMING", True)
    scan = Scan(12)
    assert merge_delta(scan, MemorySink()) == "merged"
    assert "unique" not in scan.calls
