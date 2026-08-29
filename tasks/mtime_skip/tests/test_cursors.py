from __future__ import annotations

from warehouse.fixtures_synth import chunk_files
from warehouse.jobs.cursors import unread


def test_older_unprocessed_files_stay_pending_when_output_mtime_jumps() -> None:
    files = chunk_files()
    pending = unread(files, output_mtime=90, processed_names={"chunk-new.jsonl"})
    names = {f["name"] for f in pending}
    assert names == {"chunk-old.jsonl", "chunk-mid.jsonl"}


def test_unprocessed_new_file_is_pending() -> None:
    files = chunk_files()
    pending = unread(files, output_mtime=0, processed_names=set())
    assert {f["name"] for f in pending} == {
        "chunk-old.jsonl",
        "chunk-mid.jsonl",
        "chunk-new.jsonl",
    }
