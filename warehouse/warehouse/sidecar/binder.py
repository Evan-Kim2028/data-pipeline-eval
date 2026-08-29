from __future__ import annotations

from datetime import datetime, timezone


def bind_timestamptz(value: object) -> datetime:
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc)
    label = value.isoformat() if hasattr(value, "isoformat") else value
    raise ValueError(f"Invalid timestamp with zone: {label}")
