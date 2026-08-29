from __future__ import annotations

from datetime import date


def event_at_cutoff(cutoff: date) -> object:
    return cutoff.isoformat()
