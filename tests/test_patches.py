from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from catalog import spec
from checkouts import materialize, write_checkout
from patches import (
    INVALID_PATCH_FORMAT,
    PATCH_DID_NOT_APPLY,
    PATCH_POLICY_REJECTED,
    apply_patch,
    parse_unified_diff,
)

ROOT = Path(__file__).resolve().parents[1]


def _seed(task_id: str) -> Path:
    checkout = materialize(spec(task_id), ROOT)
    dest = Path(tempfile.mkdtemp()) / "wh"
    write_checkout(checkout, dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
        cwd=dest,
        check=True,
    )
    return dest


def _git_diff(task_id: str) -> bytes:
    task = spec(task_id)
    rel = task.editable_checkout_paths[0].value
    old = ROOT / "tasks" / task_id / "fault" / rel
    new = ROOT / task.gold_repo_path.value
    proc = subprocess.run(
        ["diff", "-u", "--label", f"a/{rel}", "--label", f"b/{rel}", str(old), str(new)],
        capture_output=True,
        text=True,
    )
    body = proc.stdout
    header = f"diff --git a/{rel} b/{rel}\n"
    return (header + body).encode()


def test_valid_gold_patch_applies_once():
    task = spec("timestamptz_cutoff")
    raw = _git_diff("timestamptz_cutoff")
    parsed = parse_unified_diff(raw, tuple(p.value for p in task.editable_checkout_paths))
    work = _seed("timestamptz_cutoff")
    report = apply_patch(work, task, raw)
    assert report.status == "applied"
    assert report.changed_paths == parsed.paths
    work2 = _seed("timestamptz_cutoff")
    report2 = apply_patch(work2, task, raw)
    assert report2.response_sha256 == report.response_sha256
    assert report2.changed_paths == report.changed_paths


def test_format_failures():
    task = spec("timestamptz_cutoff")
    allowed = tuple(p.value for p in task.editable_checkout_paths)
    fenced = b"```diff\n" + _git_diff("timestamptz_cutoff") + b"```\n"
    try:
        parse_unified_diff(fenced, allowed)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert getattr(exc, "code", None) == INVALID_PATCH_FORMAT
    work = _seed("timestamptz_cutoff")
    report = apply_patch(work, task, fenced)
    assert report.status == "applied"
    try:
        parse_unified_diff(b"please fix the file\n", allowed)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert getattr(exc, "code", None) == INVALID_PATCH_FORMAT


def test_python_fence_then_diff_fence_applies_diff():
    task = spec("timestamptz_cutoff")
    gold = _git_diff("timestamptz_cutoff")
    raw = b"```python\nprint('diagnosis')\n```\n```diff\n" + gold + b"```\n"
    work = _seed("timestamptz_cutoff")
    report = apply_patch(work, task, raw)
    assert report.status == "applied"


def test_policy_and_apply_failures():
    task = spec("timestamptz_cutoff")
    allowed = tuple(p.value for p in task.editable_checkout_paths)
    traversal = b"diff --git a/../secret b/../secret\n--- a/../secret\n+++ b/../secret\n@@ -1 +1 @@\n-a\n+b\n"
    try:
        parse_unified_diff(traversal, allowed)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert getattr(exc, "code", None) in {PATCH_POLICY_REJECTED, INVALID_PATCH_FORMAT}
    tests_path = (
        b"diff --git a/tasks/x/tests/test.py b/tasks/x/tests/test.py\n"
        b"--- a/tasks/x/tests/test.py\n+++ b/tasks/x/tests/test.py\n"
        b"@@ -1 +1 @@\n-a\n+b\n"
    )
    try:
        parse_unified_diff(tests_path, allowed)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert exc.code == PATCH_POLICY_REJECTED
    undeclared = (
        b"diff --git a/warehouse/settings.py b/warehouse/settings.py\n"
        b"--- a/warehouse/settings.py\n+++ b/warehouse/settings.py\n"
        b"@@ -1 +1 @@\n-a\n+b\n"
    )
    try:
        parse_unified_diff(undeclared, allowed)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert exc.code == PATCH_POLICY_REJECTED
    deleted = (
        b"diff --git a/warehouse/sidecar/cutoff.py b/warehouse/sidecar/cutoff.py\n"
        b"--- a/warehouse/sidecar/cutoff.py\n+++ /dev/null\n"
        b"@@ -1 +0,0 @@\n-x\n"
    )
    try:
        parse_unified_diff(deleted, allowed)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert exc.code == PATCH_POLICY_REJECTED
    stale = (
        b"diff --git a/warehouse/sidecar/cutoff.py b/warehouse/sidecar/cutoff.py\n"
        b"--- a/warehouse/sidecar/cutoff.py\n+++ b/warehouse/sidecar/cutoff.py\n"
        b"@@ -1,3 +1,3 @@\n-this line is not in the file\n context\n+new\n"
    )
    work = _seed("timestamptz_cutoff")
    report = apply_patch(work, task, stale)
    assert report.status == "failed"
    assert report.failure is not None
    assert report.failure.code == PATCH_DID_NOT_APPLY
