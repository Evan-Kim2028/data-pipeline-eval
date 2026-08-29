#!/usr/bin/env python3
"""Deterministic synthetic event jsonl. Local files only.

    python scripts/gen_fixture.py --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "warehouse" / "fixtures" / "events_batch.jsonl"
UUID = "550e8400-e29b-41d4-a716-446655440000"


def rows(seed: int, n_numeric: int = 100) -> list[dict]:
    rng = random.Random(seed)
    base = datetime(2026, 8, 26, 18, 0, tzinfo=timezone.utc)
    out = []
    for i in range(n_numeric):
        out.append(
            {
                "listing_id": str(10_000_000 + i),
                "source": "market_a",
                "listing_type": "fixed",
                "price": round(10.0 + rng.random() * 8.0, 2),
                "currency": "USD",
                "sold_at": (base + timedelta(minutes=i)).isoformat(),
                "fetched_at": "2026-08-27T09:00:00+00:00",
                "title": f"Lot {i} widget",
                "url": f"https://example.invalid/a/{10_000_000 + i}",
            }
        )
    out.append(
        {
            "listing_id": UUID,
            "source": "market_b",
            "listing_type": "auction",
            "price": 40.0,
            "currency": "USD",
            "sold_at": "2026-08-26T22:11:00+00:00",
            "fetched_at": "2026-08-27T09:00:00+00:00",
            "title": "Lot 100 widget",
            "url": f"https://example.invalid/b/{UUID}",
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r) + "\n" for r in rows(args.seed))
    args.out.write_text(payload)
    print(f"wrote {args.out} seed={args.seed} bytes={len(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
