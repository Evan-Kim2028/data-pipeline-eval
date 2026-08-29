#!/usr/bin/env python3
"""Rebuild synthetic eval fixtures with a locked seed.

    python scripts/setup_eval.py --seed 42
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "warehouse"))

from gen_fixture import rows as listing_rows  # noqa: E402
from warehouse.fixtures_synth import (  # noqa: E402
    bronze_by_day,
    changelog,
    chunk_files,
    events_history,
)

FIXTURES = ROOT / "warehouse" / "fixtures"


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    seed = args.seed

    write_jsonl(FIXTURES / "events_batch.jsonl", listing_rows(seed))
    history = events_history(seed)
    write_jsonl(FIXTURES / "events_history.jsonl", history)
    write_jsonl(FIXTURES / "changelog.jsonl", changelog(seed))

    bronze_root = FIXTURES / "bronze"
    if bronze_root.exists():
        shutil.rmtree(bronze_root)
    bronze = bronze_by_day(seed)
    for day, recs in bronze.items():
        write_jsonl(bronze_root / f"dt={day}" / "part.jsonl", recs)

    chunks_root = FIXTURES / "chunks"
    if chunks_root.exists():
        shutil.rmtree(chunks_root)
    chunks_root.mkdir(parents=True)
    for spec in chunk_files():
        path = chunks_root / spec["name"]
        path.write_text("{}\n")
        os.utime(path, times=(spec["mtime"], spec["mtime"]))

    print(
        f"setup_eval seed={seed} history_rows={len(history)} days={len(bronze)} "
        f"out={FIXTURES}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
