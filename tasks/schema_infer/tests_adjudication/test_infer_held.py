from __future__ import annotations

from warehouse.silver.schema import infer_listing_id_kind

UUID = "550e8400-e29b-41d4-a716-446655440000"


def test_infer_sees_uuid_past_the_head_sample() -> None:
    rows = [{"listing_id": str(10_000_000 + i)} for i in range(100)]
    rows.append({"listing_id": UUID})
    assert infer_listing_id_kind(rows) is str


def test_empty_batch_stays_string_kind() -> None:
    assert infer_listing_id_kind([]) is str
