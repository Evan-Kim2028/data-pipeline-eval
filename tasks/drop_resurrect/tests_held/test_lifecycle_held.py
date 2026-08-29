from __future__ import annotations

import pytest
from warehouse.jobs.table_open import open_for_write
from warehouse.lifecycle import Catalog


def test_tombstone_survives_unrelated_writer() -> None:
    cat = Catalog()
    cat.create("gold.a")
    cat.drop("gold.a")
    cat.create("gold.b")
    assert "gold.a" in cat.tombstones
    with pytest.raises(RuntimeError, match="dropped"):
        open_for_write(cat, "gold.a")
