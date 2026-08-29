from __future__ import annotations

import pytest
from warehouse.jobs.table_open import open_for_write
from warehouse.lifecycle import Catalog


def test_drop_then_get_or_create_does_not_resurrect() -> None:
    cat = Catalog()
    cat.create("gold.events")
    cat.drop("gold.events")
    with pytest.raises(RuntimeError, match="dropped"):
        open_for_write(cat, "gold.events")
    assert "gold.events" not in cat.tables


def test_undropped_table_opens() -> None:
    cat = Catalog()
    cat.create("gold.events")
    assert open_for_write(cat, "gold.events") is cat.tables["gold.events"]


def test_never_seen_name_creates_and_drop_stays_dead() -> None:
    cat = Catalog()
    first = open_for_write(cat, "gold.new")
    second = open_for_write(cat, "gold.new")
    assert first is second
    cat.drop("gold.new")
    with pytest.raises(RuntimeError, match="dropped"):
        open_for_write(cat, "gold.new")
