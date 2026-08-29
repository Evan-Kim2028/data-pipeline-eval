from __future__ import annotations

from pathlib import Path

import warehouse
from warehouse.silver.load import load_listing_ids

FIXTURE = Path(warehouse.__file__).resolve().parent.parent / "fixtures" / "events_batch.jsonl"


def test_numeric_head_then_uuid_in_same_batch() -> None:
    lines = [f'{{"listing_id": "{10_000_000 + i}"}}' for i in range(100)]
    lines.append('{"listing_id": "550e8400-e29b-41d4-a716-446655440000"}')
    got = load_listing_ids(lines)
    assert len(got) == 101
    assert got[0] == "10000000"
    assert got[-1] == "550e8400-e29b-41d4-a716-446655440000"


def test_all_numeric() -> None:
    assert load_listing_ids(['{"listing_id": "42"}', '{"listing_id": "99"}']) == ["42", "99"]


def test_fixture_batch_has_mixed_ids() -> None:
    got = load_listing_ids(FIXTURE.read_text().splitlines())
    assert got[0] == "10000000"
    assert got[-1] == "550e8400-e29b-41d4-a716-446655440000"
