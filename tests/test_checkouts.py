from __future__ import annotations

from pathlib import Path

from harness.catalog import spec, validate_catalog
from harness.checkouts import entrypoint_source, materialize

ROOT = Path(__file__).resolve().parents[1]


def test_materialize_applies_the_fault_and_keeps_entrypoint():
    task = spec("schema_infer")
    first = materialize(task, ROOT)
    second = materialize(task, ROOT)
    assert first.checkout_digest == second.checkout_digest
    files = first.file_map()
    gold = (ROOT / task.gold_repo_path.value).read_bytes()
    faulted = files["warehouse/silver/schema.py"]
    assert faulted != gold
    entrypoint_source(task, first)


def test_every_catalog_task_materializes():
    assert validate_catalog(ROOT) == []
    for task_id in (
        "schema_infer",
        "unique_probe",
        "timestamptz_cutoff",
        "utc_lookback",
        "late_event_close",
    ):
        checkout = materialize(spec(task_id), ROOT)
        assert checkout.task_id == task_id
        assert checkout.ordered_hashes
