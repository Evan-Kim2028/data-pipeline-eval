from __future__ import annotations

from warehouse.settings import GOLD_NAMESPACE, SILVER_NAMESPACE


def namespaces() -> tuple[str, str]:
    return SILVER_NAMESPACE, GOLD_NAMESPACE


def ok() -> dict[str, str]:
    return {"status": "ok", "silver": SILVER_NAMESPACE, "gold": GOLD_NAMESPACE}
