"""Classify a patched tree: gold / equivalent / other.

gold: fault overlay files now match the gold warehouse, nothing else changed.
equivalent: only those files changed, but the text is not byte-identical
(documented "also green" patches).
other: extra files changed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAREHOUSE = ROOT / "warehouse"


def fault_rels(task: str) -> set[str]:
    fault = ROOT / "tasks" / task / "fault"
    if not fault.is_dir():
        return set()
    return {p.relative_to(fault).as_posix() for p in fault.rglob("*") if p.is_file()}


def changed_rels(work: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=work,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in proc.stdout.splitlines() if line and not line.startswith(".git")}


def classify(task: str, work: Path) -> dict:
    fault = fault_rels(task)
    changed = changed_rels(work)
    extra = sorted(changed - fault)
    gold_match = True
    for rel in sorted(fault):
        got = work / rel
        exp = WAREHOUSE / rel
        if not got.is_file() or not exp.is_file() or got.read_text() != exp.read_text():
            gold_match = False
            break
    if gold_match and not extra:
        tag = "gold"
    elif not extra:
        tag = "equivalent"
    else:
        tag = "other"
    return {
        "quality": tag,
        "changed": sorted(changed),
        "extra": extra,
        "fault_files": sorted(fault),
    }
