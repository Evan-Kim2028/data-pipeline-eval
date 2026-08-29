from __future__ import annotations

from datetime import date

from warehouse.sidecar.binder import bind_timestamptz
from warehouse.sidecar.cutoff import event_at_cutoff


def lookback_bound(cutoff: date) -> object:
    return bind_timestamptz(event_at_cutoff(cutoff))
