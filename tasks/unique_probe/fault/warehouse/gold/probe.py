from __future__ import annotations

from warehouse.settings import STREAMING


def delta_is_nonempty(scan) -> bool:
    deduped = scan.unique()
    probe = deduped.limit(1)
    if STREAMING:
        return probe.collect(engine="streaming").height > 0
    return probe.collect().height > 0
