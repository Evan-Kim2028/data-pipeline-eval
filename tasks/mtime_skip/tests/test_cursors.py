from __future__ import annotations

from warehouse.fixtures_synth import chunk_files
from warehouse.jobs.cursors import unread
from warehouse.serving_cursors import pending_files


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


def test_poison_output_mtime_is_unused() -> None:
    class Poison:
        def __gt__(self, other):
            raise AssertionError("mtime")

        def __lt__(self, other):
            raise AssertionError("mtime")

        def __ge__(self, other):
            raise AssertionError("mtime")

        def __le__(self, other):
            raise AssertionError("mtime")

    files = [{"name": "a", "mtime": 1}, {"name": "b", "mtime": 9}]
    names = {f["name"] for f in pending_files(files, Poison(), {"b"})}
    assert names == {"a"}
