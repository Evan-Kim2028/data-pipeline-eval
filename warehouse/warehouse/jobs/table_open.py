from __future__ import annotations

from warehouse.lifecycle import Catalog


def open_for_write(catalog: Catalog, name: str) -> dict:
    return catalog.get_or_create(name)
