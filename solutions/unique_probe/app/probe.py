from __future__ import annotations

from app.config import STREAMING


def delta_is_nonempty(scan) -> bool:
    """True if the incoming delta has any rows.

    Probe the un-deduped scan. unique() of the delta is a full plan.
    """
    probe = scan.limit(1)
    if STREAMING:
        return probe.collect(engine="streaming").height > 0
    return probe.collect().height > 0
