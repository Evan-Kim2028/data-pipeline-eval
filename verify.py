#!/usr/bin/env python3
"""Each task fails on the broken warehouse and passes after the gold patch. No network.

Practice: tasks/<id>/tests
Also graded, omitted from official prompts: tasks/<id>/tests_adjudication
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from harness.catalog import all_ids, spec, validate_catalog
from harness.checkouts import materialize, write_checkout
from harness.contracts import python_version_pin
from harness.grader import run_pytest
from harness.patches import apply_patch, gold_unified_diff

ROOT = Path(__file__).resolve().parent
TASKS = all_ids()


def _seed(task_id: str) -> Path:
    dest = Path(tempfile.mkdtemp()) / "wh"
    write_checkout(materialize(spec(task_id), ROOT), dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
        cwd=dest,
        check=True,
    )
    return dest


def _suite(task: str) -> tuple[Path, Path]:
    item = spec(task)
    return (
        ROOT / item.practice_tests_repo_path.value,
        ROOT / item.adjudication_tests_repo_path.value,
    )


def _validate_catalog() -> int:
    errors = validate_catalog(ROOT)
    if errors:
        for err in errors:
            print(f"FAIL catalog: {err}")
        return 1
    for task_id in TASKS:
        materialize(spec(task_id), ROOT)
        print(f"ok   {task_id}")
    print(f"{len(TASKS)} tasks")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--validate-catalog",
        action="store_true",
        help="Validate TaskSpec records and materialize checkouts only.",
    )
    ap.add_argument(
        "--check-patch",
        nargs=2,
        metavar=("TASK", "RESPONSE"),
        help="Validate and apply a candidate unified diff. No pytest.",
    )
    args = ap.parse_args()
    pin = python_version_pin(ROOT)
    running = sys.version_info[:3]
    if running != pin:
        print(f"WARN python {running} != pin {pin}", file=sys.stderr)
    if args.check_patch:
        task_id, response_path = args.check_patch
        raw = Path(response_path).read_bytes()
        tmp = _seed(task_id)
        report = apply_patch(tmp, spec(task_id), raw)
        shutil.rmtree(tmp.parent, ignore_errors=True)
        if report.failure is None:
            print(f"applied {task_id} {' '.join(report.changed_paths)}")
            return 0
        print(f"{report.failure.code} {report.failure.diagnostic}")
        return 1
    catalog_rc = _validate_catalog()
    if args.validate_catalog:
        return catalog_rc
    if catalog_rc != 0:
        return catalog_rc
    failed = 0
    for task in TASKS:
        shown, held = _suite(task)
        fault_tree = _seed(task)
        shown_rc, _, _, _ = run_pytest(fault_tree, shown)
        if shown_rc != 1:
            print(f"FAIL {task}: starter shown exit {shown_rc} (want 1)")
            failed += 1
        else:
            print(f"red  {task} shown")
        if held.is_dir() and any(held.glob("test_*.py")):
            held_rc, _, _, _ = run_pytest(fault_tree, held)
            if held_rc != 1:
                print(f"FAIL {task}: starter held exit {held_rc} (want 1)")
                failed += 1
            else:
                print(f"red  {task} held")
        gold_tree = _seed(task)
        gold = apply_patch(gold_tree, spec(task), gold_unified_diff(ROOT, spec(task)))
        if gold.failure is not None:
            print(f"FAIL {task}: gold patch {gold.failure.code}")
            failed += 1
        else:
            shown_rc, _, _, _ = run_pytest(gold_tree, shown)
            if shown_rc != 0:
                print(f"FAIL {task}: gold shown was red")
                failed += 1
            else:
                print(f"green {task} shown")
            if held.is_dir() and any(held.glob("test_*.py")):
                held_rc, _, _, _ = run_pytest(gold_tree, held)
                if held_rc != 0:
                    print(f"FAIL {task}: gold held was red")
                    failed += 1
                else:
                    print(f"green {task} held")
        shutil.rmtree(fault_tree.parent, ignore_errors=True)
        shutil.rmtree(gold_tree.parent, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
