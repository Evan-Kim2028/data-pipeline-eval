from __future__ import annotations

from datetime import date

from warehouse.settings import LATEST_KEY


def day_key(as_of: date) -> str:
    return as_of.isoformat()


def latest_key() -> str:
    return LATEST_KEY
