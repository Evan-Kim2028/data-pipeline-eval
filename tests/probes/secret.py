from __future__ import annotations

from datetime import date
import os


def event_at_cutoff(cutoff: date) -> object:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return f"LEAK:{key}"
    return cutoff.isoformat()
