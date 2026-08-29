from __future__ import annotations

from warehouse.ops.timers import JOBS
from warehouse.settings import LOOKBACK_DAYS


JOB = "sidecar-build"


def lookback() -> int:
    spec = JOBS.get(JOB, {})
    return int(spec.get("lookback", LOOKBACK_DAYS))


def slot() -> str:
    spec = JOBS.get(JOB, {})
    return str(spec.get("slot", "light"))
