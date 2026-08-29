from __future__ import annotations

from warehouse.serving_cursors import pending_files


def unread(
    files: list[dict],
    output_mtime: int,
    processed_names: set[str],
) -> list[dict]:
    return pending_files(files, output_mtime, processed_names)
