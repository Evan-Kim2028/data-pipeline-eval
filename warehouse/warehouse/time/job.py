from __future__ import annotations

from warehouse.settings import LOOKBACK_DAYS
from warehouse.time.lookback import lookback_since


def window_start(days: int | None = None):
    return lookback_since(LOOKBACK_DAYS if days is None else days)
