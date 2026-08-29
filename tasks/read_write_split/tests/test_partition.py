from __future__ import annotations

from warehouse.incremental.partition_io import read_day
from warehouse.jobs.partition_io import overwrite_day


def test_overwrite_one_day_does_not_read_other_days() -> None:
    bronze = {
        "2026-08-01": [{"event_id": "old-1"}],
        "2026-08-02": [{"event_id": "old-2"}],
    }
    got = overwrite_day(bronze, "2026-08-01", [{"event_id": "new-1"}])
    assert got == [{"event_id": "new-1"}]
    assert read_day(bronze, "2026-08-02") == [{"event_id": "old-2"}]
