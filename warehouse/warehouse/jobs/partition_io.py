from __future__ import annotations

from warehouse.incremental.partition_io import read_day, write_day


def overwrite_day(bronze: dict[str, list[dict]], day: str, rows: list[dict]) -> list[dict]:
    write_day(bronze, day, rows)
    return read_day(bronze, day)
