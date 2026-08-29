from __future__ import annotations

from warehouse.jobs.cursors import unread


def test_processed_old_file_is_not_pending() -> None:
    files = [
        {"name": "chunk-old.jsonl", "mtime": 10},
        {"name": "chunk-new.jsonl", "mtime": 80},
    ]
    pending = unread(files, output_mtime=90, processed_names={"chunk-old.jsonl"})
    assert {f["name"] for f in pending} == {"chunk-new.jsonl"}
