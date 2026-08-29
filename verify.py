#!/usr/bin/env python3
"""Red starters (warehouse + fault) / green gold warehouse. No network.

Shown tests: tasks/<id>/tests
Held-out tests: tasks/<id>/tests_held (not sent to the model)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from catalog import all_ids

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
    base = ROOT / "tasks" / task
    return base / "tests", base / "tests_held"


def main() -> int:
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
