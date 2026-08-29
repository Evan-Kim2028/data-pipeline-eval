from __future__ import annotations

from datetime import date, datetime, timezone


def local_today() -> date:
    return date.today()


def utc_today() -> date:
    return datetime.now(timezone.utc).date()
