from __future__ import annotations

import pytest
from warehouse.incremental.basis import merge_incoming
from warehouse.jobs.frozen_basis import merge_first_load


def test_empty_existing_does_not_plan_unique() -> None:
    incoming = [{"entity_id": "ent-000", "event_id": "a"}]

    def unique_fn(rows):
        raise MemoryError("unique planned against empty basis")

    assert merge_first_load(incoming, unique_fn) == incoming


def test_nonempty_existing_still_uniques() -> None:
    existing = [{"entity_id": "ent-000", "event_id": "a"}]
    incoming = [
        {"entity_id": "ent-000", "event_id": "a"},
        {"entity_id": "ent-001", "event_id": "b"},
    ]

    def unique_fn(rows):
        seen: set[str] = set()
        out = []
        for row in rows:
            key = row["event_id"]
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        return out

    out = merge_incoming(existing, incoming, unique_fn)
    assert [row["event_id"] for row in out] == ["a", "b"]


def test_unique_is_not_required_on_first_load() -> None:
    try:
        merge_first_load([{"event_id": "a"}], lambda rows: (_ for _ in ()).throw(MemoryError("unique")))
    except MemoryError:
        pytest.fail("unique() was planned on an empty existing snapshot")
