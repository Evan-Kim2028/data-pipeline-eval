from __future__ import annotations


def pending_by_mtime(files: list[dict], output_mtime: int) -> list[dict]:
    return [f for f in files if f["mtime"] > output_mtime]


def pending_files(
    files: list[dict],
    output_mtime: int,
    processed_names: set[str],
) -> list[dict]:
    return [f for f in files if f["mtime"] > output_mtime]
