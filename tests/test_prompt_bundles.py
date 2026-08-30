from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.catalog import TASKS, all_ids
from harness.prompt_bundle import SHARED_INSTRUCTIONS, all_bundles, bundle_for

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "tests" / "snapshots" / "prompt-sha256.json"


def test_render_is_deterministic_and_hashed_over_exact_bytes():
    first = bundle_for("schema_infer", ROOT)
    second = bundle_for("schema_infer", ROOT)
    assert first.content == second.content
    assert first.sha256 == hashlib.sha256(first.content).hexdigest()
    assert first.content.endswith(b"\n")
    assert b"\r" not in first.content
    text = first.content.decode("utf-8")
    assert "## Entrypoint" in text
    assert "warehouse.silver.load.load_listing_ids" in text
    assert "warehouse/silver/schema.py" in text
    assert "### tests/" not in text
    assert "docs/solutions/" not in text
    assert ".git/" not in text


def test_all_official_prompts_match_snapshot_and_omit_denied_paths():
    bundles = all_bundles(ROOT)
    assert tuple(bundles) == all_ids()
    snap = json.loads(SNAPSHOT.read_text())
    assert snap["schema_version"] == "1"
    assert set(snap["tasks"]) == set(all_ids())
    denied = (
        b"tests_held/",
        b"docs/solutions/",
        b"solutions/",
        b"__pycache__",
        b".pytest_cache",
    )
    for task_id, bundle in bundles.items():
        rec = snap["tasks"][task_id]
        assert rec["sha256"] == bundle.sha256
        assert rec["byte_length"] == len(bundle.content)
        for marker in denied:
            assert marker not in bundle.content
        assert bundle.entrypoint == next(t.entrypoint for t in TASKS if t.id == task_id)
        assert bundle.ordered_context_paths[0] in bundle.content.decode("utf-8")


def test_snapshot_has_exactly_fifteen_tasks():
    snap = json.loads(SNAPSHOT.read_text())
    assert len(snap["tasks"]) == 15


def test_cot_scaffold_is_unbiased():
    text = SHARED_INSTRUCTIONS.lower()
    assert "held-out" not in text
    assert "pytest" not in text
    assert "state each reasoning claim once" in text
    for task in TASKS:
        line = task.one_liner.strip()
        if line:
            assert line.lower() not in text
