from __future__ import annotations

import random
from datetime import date, timedelta

SEED = 42
TODAY = date(2026, 8, 27)
N_ENTITIES = 5
N_DAYS = 90
UUID = "550e8400-e29b-41d4-a716-446655440000"


def events_history(seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    for e in range(N_ENTITIES):
        entity = f"ent-{e:03d}"
        for d in range(N_DAYS):
            day = TODAY - timedelta(days=N_DAYS - 1 - d)
            rows.append(
                {
                    "event_id": f"{entity}-{day.isoformat()}",
                    "entity_id": entity,
                    "source": "market_a",
                    "amount": round(1.0 + rng.random() * 20.0, 2),
                    "event_at": day.isoformat(),
                    "processing_at": day.isoformat(),
                }
            )
    rows.append(
        {
            "event_id": "ent-000-late",
            "entity_id": "ent-000",
            "source": "market_a",
            "amount": 9.5,
            "event_at": (TODAY - timedelta(days=1)).isoformat(),
            "processing_at": TODAY.isoformat(),
        }
    )
    return rows


def bronze_by_day(seed: int = SEED) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in events_history(seed):
        out.setdefault(row["event_at"], []).append(row)
    return out


def changelog(seed: int = SEED) -> list[dict]:
    del seed
    return [
        {
            "entity_id": "ent-000",
            "changed_at": (TODAY - timedelta(days=1)).isoformat(),
        },
        {
            "entity_id": "ent-001",
            "changed_at": (TODAY - timedelta(days=60)).isoformat(),
        },
    ]


def chunk_files() -> list[dict]:
    return [
        {"name": "chunk-old.jsonl", "mtime": 10},
        {"name": "chunk-mid.jsonl", "mtime": 40},
        {"name": "chunk-new.jsonl", "mtime": 80},
    ]


def mixed_listing_rows() -> list[dict]:
    rows = [{"listing_id": str(10_000_000 + i), "source": "market_a"} for i in range(100)]
    rows.append({"listing_id": UUID, "source": "market_b"})
    return rows
