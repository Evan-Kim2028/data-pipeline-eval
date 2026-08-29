from __future__ import annotations


def write_day(bronze: dict[str, list[dict]], day: str, rows: list[dict]) -> None:
    bronze[day] = list(rows)


def read_all(bronze: dict[str, list[dict]]) -> list[dict]:
    out: list[dict] = []
    for rows in bronze.values():
        out.extend(rows)
    return out


def read_day(bronze: dict[str, list[dict]], day: str) -> list[dict]:
    return read_all(bronze)
