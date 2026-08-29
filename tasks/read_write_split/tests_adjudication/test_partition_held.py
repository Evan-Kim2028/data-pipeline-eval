from __future__ import annotations

from warehouse.incremental.partition_io import read_day, write_day


def test_second_day_write_does_not_change_first() -> None:
    bronze: dict[str, list[dict]] = {}
    write_day(bronze, "2026-08-01", [{"event_id": "a"}])
    write_day(bronze, "2026-08-02", [{"event_id": "b"}])
    assert read_day(bronze, "2026-08-01") == [{"event_id": "a"}]
    assert read_day(bronze, "2026-08-02") == [{"event_id": "b"}]
