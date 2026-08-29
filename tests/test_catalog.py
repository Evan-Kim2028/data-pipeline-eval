from __future__ import annotations

from pathlib import Path

from catalog import TASKS, all_ids, default_ids, spec, validate_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_covers_exactly_the_task_directories():
    assert len(TASKS) == 15
    assert all_ids() == tuple(t.id for t in TASKS)
    assert len(default_ids()) == 13
    assert spec("schema_infer").entrypoint == "warehouse.silver.load.load_listing_ids"


def test_validate_catalog_accepts_the_public_tree():
    errors = validate_catalog(ROOT)
    assert errors == []


def test_task_specs_keep_gold_in_warehouse_and_edits_on_fault_files():
    for task in TASKS:
        assert task.gold_repo_path.value.startswith("warehouse/warehouse/")
        assert task.editable_checkout_paths[0].value.startswith("warehouse/")
        assert task.prompt_repo_path.value.endswith("prompt.txt")
