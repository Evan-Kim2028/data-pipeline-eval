# Categories and difficulty

Task **names** stay as the directory ids (`schema_infer`, …).
**Category** clusters them. **Difficulty** is an estimate until a
pinned campaign publishes pass rates. Campaign difficulty is one
minus that task's end-to-end rate and does not replace these labels.

## Categories

| id | Label | What the incident is about |
|---|---|---|
| `schema` | Schema & types | Inferred dtypes, binders, mixed ids |
| `time` | Time & calendars | Host clock vs warehouse dates |
| `incremental` | Incremental I/O | Cheap probes that plan full work |
| `serving` | Serving contracts | What readers / next run treat as current or done |
| `concurrency` | Concurrent writers | Stale handles, OCC retry |

`latest_pointer`, `watermark_poison`, `mtime_skip`, and
`drop_resurrect` share **serving**. `entity_reload`, `frozen_basis`,
`read_write_split`, and `rebuild_wipe` share **incremental**.
`schema_infer` and `field_readd` are **schema**. `late_event_close`
and `utc_lookback` share **time**. `occ_retry` is **concurrency**.
`timestamptz_cutoff` is calibration **schema**.

## Difficulty (estimated)

Defined for this harness: one-shot unified diff, no tools, messy
production tree, public tests omitted from candidate messages.

| Level | Means |
|---|---|
| `easy` | Causal line is in the module the prompt points at. One invariant. |
| `med` | Must pick the right file among distractors. Equivalent gold patches exist. |
| `hard` | A correct helper used in the wrong place, or a comment that lies about cost. |
| `very_hard` | Ordering. A patch that only satisfies the happy path fails the abort test. |

Source of truth: `harness/catalog.py`.
