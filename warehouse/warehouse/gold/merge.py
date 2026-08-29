from __future__ import annotations

from warehouse.gold.probe import delta_is_nonempty


def merge_delta(scan, sink) -> str:
    if not delta_is_nonempty(scan):
        return "empty"
    sink.write("merged")
    return "merged"
