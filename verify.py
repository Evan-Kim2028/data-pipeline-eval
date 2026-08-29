#!/usr/bin/env python3
"""Red starters (warehouse + fault) / green gold warehouse. No network.

Practice tests: tasks/<id>/tests
Adjudication tests: tasks/<id>/tests_held (public, omitted from official prompts)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from catalog import all_ids, spec, validate_catalog
from checkouts import materialize, write_checkout
from contracts import python_version_pin
from patches import apply_patch

ROOT = Path(__file__).resolve().parent
WAREHOUSE = ROOT / "warehouse"
TASKS = all_ids()


def _pytest(tree: Path, tests: Path) -> int:
    if not tests.is_dir() or not any(tests.glob("test_*.py")):
        return 0
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tree)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(tests)],
        cwd=tree,
        env=env,
        capture_output=True,
    ).returncode


def _tree_with_fault(task: str) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "wh"
    shutil.copytree(WAREHOUSE, tmp)
    fault = ROOT / "tasks" / task / "fault"
    if fault.exists():
        shutil.copytree(fault, tmp, dirs_exist_ok=True)
    return tmp


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
        checkout = materialize(spec(task_id), ROOT)
        tmp = Path(tempfile.mkdtemp()) / "wh"
        write_checkout(checkout, tmp)
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)
        subprocess.run(
            ["git", "-c", "user.email=eval@local", "-c", "user.name=eval", "commit", "-qm", "seed"],
            cwd=tmp,
            check=True,
        )
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
        fault_tree = _tree_with_fault(task)
        if _pytest(fault_tree, shown) == 0:
            print(f"FAIL {task}: starter was green (shown)")
            failed += 1
        else:
            print(f"red  {task} shown")
        if held.is_dir() and any(held.glob("test_*.py")):
            if _pytest(fault_tree, held) == 0:
                print(f"FAIL {task}: starter was green (held-out)")
                failed += 1
            else:
                print(f"red  {task} held")
        if _pytest(WAREHOUSE, shown) != 0:
            print(f"FAIL {task}: gold warehouse was red (shown)")
            failed += 1
        else:
            print(f"green {task} shown")
        if held.is_dir() and any(held.glob("test_*.py")):
            if _pytest(WAREHOUSE, held) != 0:
                print(f"FAIL {task}: gold warehouse was red (held-out)")
                failed += 1
            else:
                print(f"green {task} held")
        shutil.rmtree(fault_tree.parent, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
