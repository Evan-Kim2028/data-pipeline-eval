#!/usr/bin/env python3
"""Why-diff for a provider bake-off jsonl.

  python scripts/compare_trials.py logs/runs/<run_id>.jsonl

Prints pass/quality/applied sha per host and whether applied diffs match.
Does not call OpenRouter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def _sig(row: dict) -> str | None:
    path = row.get("applied_diff_path")
    if path:
        target = Path(path)
        if target.is_file():
            return hashlib.sha256(target.read_bytes()).hexdigest()
    sha = row.get("applied_sha256")
    if sha:
        return str(sha)
    return None


def compare_rows(rows: list[dict]) -> str:
    by: dict[tuple, dict] = defaultdict(dict)
    providers: list[str] = []
    for row in rows:
        p = str(row.get("provider") or "")
        if p and p not in providers:
            providers.append(p)
        task = row["task"]
        trial = int(row.get("trial") or 1)
        by[(task, trial)][p] = row
    lines = [
        f"{'task':22} {'tr':2} " + "".join(f"{p:22}" for p in providers) + " same_diff"
    ]
    for (task, trial), hosts in sorted(by.items()):
        cells: list[str] = []
        sigs: list[str | None] = []
        for p in providers:
            r = hosts.get(p)
            if r is None:
                cells.append(f"{'—':22}")
                sigs.append(None)
                continue
            mark = "P" if r.get("pass") else "F"
            q = str(r.get("quality") or "")[:10]
            sha8 = str(r.get("applied_sha256") or "")[:8]
            cells.append(f"{mark}/{q}/{sha8}")
            sigs.append(_sig(r))
        present = [s for s in sigs if s]
        same = ""
        if len(present) >= 2:
            same = "yes" if len(set(present)) == 1 else "no"
        lines.append(
            f"{task:22} {trial:<2} " + "".join(f"{c:22}" for c in cells) + f" {same}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", type=Path)
    args = ap.parse_args()
    rows = [json.loads(line) for line in args.jsonl.read_text().splitlines() if line.strip()]
    print(compare_rows(rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
