#!/usr/bin/env python3
"""Red starters (warehouse + fault) / green gold warehouse. No network."""

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


def main() -> int:
    failed = 0
    for task in TASKS:
        tests = ROOT / "tasks" / task / "tests"
        red = _pytest(_tree_with_fault(task), tests)
        if red == 0:
            print(f"FAIL {task}: starter was green")
            failed += 1
        else:
            print(f"red  {task}")
        green = _pytest(WAREHOUSE, tests)
        if green != 0:
            print(f"FAIL {task}: gold warehouse was red")
            failed += 1
        else:
            print(f"green {task}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
