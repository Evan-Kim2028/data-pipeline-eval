from __future__ import annotations

from warehouse.settings import LOOKBACK_DAYS, SIDECAR_LOOKBACK_DAYS

JOBS = {
    "silver-load": {"lookback": LOOKBACK_DAYS, "slot": "light"},
    "gold-merge": {"lookback": LOOKBACK_DAYS, "slot": "heavy"},
    "sidecar": {"lookback": SIDECAR_LOOKBACK_DAYS, "slot": "light"},
    "history-backfill": {"lookback": LOOKBACK_DAYS, "slot": "heavy"},
    "window-drain": {"lookback": LOOKBACK_DAYS, "slot": "heavy"},
}


def job_names() -> list[str]:
    return sorted(JOBS)
