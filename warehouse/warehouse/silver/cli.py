from __future__ import annotations

import argparse
from pathlib import Path

from warehouse.silver.load import load_listing_ids
from warehouse.silver.report import summarize


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="silver-load")
    p.add_argument("jsonl", type=Path, nargs="?", default=Path("fixtures/events_batch.jsonl"))
    args = p.parse_args(argv)
    ids = load_listing_ids(args.jsonl.read_text().splitlines())
    print(summarize(ids))
    return 0
