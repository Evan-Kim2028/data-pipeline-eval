"""Task catalog: name, category, difficulty.

Difficulty is *estimated* until a pinned-host run fills pass@1.
See docs/TAXONOMY.md.
"""

from __future__ import annotations

CATEGORIES = {
    "schema": {
        "label": "Schema & types",
        "about": "Inferred dtypes, warehouse binders, mixed ids in one batch.",
    },
    "time": {
        "label": "Time & calendars",
        "about": "Which clock the job uses for lookbacks and cutoffs.",
    },
    "incremental": {
        "label": "Incremental I/O",
        "about": "Cheap emptiness/skip probes that accidentally plan full work.",
    },
    "serving": {
        "label": "Serving contracts",
        "about": "What readers or the next run treat as current or done.",
    },
    "concurrency": {
        "label": "Concurrent writers",
        "about": "Stale handles, OCC, retry that does not re-read.",
    },
}

TASKS = (
    {
        "id": "schema_infer",
        "category": "schema",
        "difficulty": "med",
        "suite": "default",
        "one_liner": "Head-sample infers int; later UUID in the same batch.",
    },
    {
        "id": "unique_probe",
        "category": "incremental",
        "difficulty": "hard",
        "suite": "default",
        "one_liner": "unique().limit(1) still plans a full unique.",
    },
    {
        "id": "latest_pointer",
        "category": "serving",
        "difficulty": "hard",
        "suite": "default",
        "one_liner": "History backfill overwrites the serving 'latest' pointer.",
    },
    {
        "id": "occ_retry",
        "category": "concurrency",
        "difficulty": "hard",
        "suite": "default",
        "one_liner": "OCC retry reuses a stale table handle.",
    },
    {
        "id": "watermark_poison",
        "category": "serving",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Watermark advances before the window commits.",
    },
    {
        "id": "entity_reload",
        "category": "incremental",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Watermark picks changed keys; scan has no time predicate.",
    },
    {
        "id": "frozen_basis",
        "category": "incremental",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Chunk unique()s against a start-of-run snapshot with no existing rows.",
    },
    {
        "id": "read_write_split",
        "category": "incremental",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Partitioned overwrite; the read still walks the full bronze tree.",
    },
    {
        "id": "mtime_skip",
        "category": "serving",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Crash mid-chunk; output mtime treats unread older files as consumed.",
    },
    {
        "id": "rebuild_wipe",
        "category": "incremental",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Rebuild retry wipes staging checkpoints and restarts at record one.",
    },
    {
        "id": "drop_resurrect",
        "category": "serving",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Catalog drop; next writer get_or_create recreates the table.",
    },
    {
        "id": "field_readd",
        "category": "schema",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Drop then re-add the same column name; old field identity is reused.",
    },
    {
        "id": "late_event_close",
        "category": "time",
        "difficulty": "very_hard",
        "suite": "default",
        "one_liner": "Processing-time close marks the event-time window done; late facts vanish.",
    },
    {
        "id": "timestamptz_cutoff",
        "category": "schema",
        "difficulty": "easy",
        "suite": "calibration",
        "one_liner": "date.isoformat() bound into timestamptz.",
    },
    {
        "id": "utc_lookback",
        "category": "time",
        "difficulty": "med",
        "suite": "calibration",
        "one_liner": "date.today() vs UTC around midnight.",
    },
)


def default_ids() -> tuple[str, ...]:
    return tuple(t["id"] for t in TASKS if t["suite"] == "default")


def all_ids() -> tuple[str, ...]:
    return tuple(t["id"] for t in TASKS)
