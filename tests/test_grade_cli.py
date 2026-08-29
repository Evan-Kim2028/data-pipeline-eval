from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

from catalog import spec
from checkouts import materialize, write_checkout
from grade import _tar_bytes
from patches import gold_unified_diff

ROOT = Path(__file__).resolve().parents[1]


def test_task_archive_has_faulted_checkout_and_public_tests_only():
    task = spec("timestamptz_cutoff")
    checkout = materialize(task, ROOT)
    tmp = Path(tempfile.mkdtemp()) / "co"
    write_checkout(checkout, tmp)
    blob = _tar_bytes(tmp, "timestamptz_cutoff")
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r") as tar:
        names = tar.getnames()
    assert any(n.startswith("checkout/") for n in names)
    assert any(n.startswith("tests/") for n in names)
    assert any(n.startswith("tests_adjudication/") for n in names)
    assert "policy.json" in names
    joined = "\n".join(names)
    assert "docs/solutions" not in joined
    assert "/mutants/" not in joined
    assert ".git/" not in joined
    member = tarfile.open(fileobj=io.BytesIO(blob), mode="r")
    cutoff = member.extractfile("checkout/warehouse/sidecar/cutoff.py").read()
    gold = (ROOT / task.gold_repo_path.value).read_bytes()
    assert cutoff != gold


def test_grade_modules_do_not_import_providers():
    for name in ("grade.py", "grader.py", "sandbox.py"):
        text = (ROOT / name).read_text()
        assert "import run_providers" not in text
        assert "from run_providers" not in text


def test_gold_diff_is_a_strict_unified_patch():
    raw = gold_unified_diff(ROOT, spec("timestamptz_cutoff"))
    assert raw.startswith(b"diff --git a/warehouse/sidecar/cutoff.py")
    assert b"```" not in raw
