# Categories and difficulty

Task **names** stay as the directory ids (`schema_infer`, …).
**Category** clusters them. **Difficulty** is an estimate until we
have pass rates.

## Categories

| id | Label | What the incident is about |
|---|---|---|
| `schema` | Schema & types | Inferred dtypes, binders, mixed ids |
| `time` | Time & calendars | Host clock vs warehouse dates |
| `incremental` | Incremental I/O | “Cheap” probes that plan full work |
| `serving` | Serving contracts | What readers / next run treat as current or done |
| `concurrency` | Concurrent writers | Stale handles, OCC retry |

`latest_pointer` and `watermark_poison` share **serving**: both
advertise a state that is not the committed truth. One is the
latest-day pointer; the other is the checkpoint.

## Difficulty (estimated)

Defined for **this gym’s harness**: one-shot unified diff, no tools,
messy `app/` package, hidden tests. Not SWE-bench “hours in a repo.”

| Level | Means |
|---|---|
| `easy` | Causal line is in the module the prompt points at. One invariant. |
| `med` | Must pick the right file among distractors (`legacy.py`, config knobs). Equivalent gold patches exist. |
| `hard` | A *correct* helper used in the wrong place, or a comment that lies about cost. Hidden spy/invariant. |
| `very_hard` | Ordering (commit vs checkpoint). A patch that only satisfies the happy path fails the abort test. |

These labels are **estimated**, not measured. After a `--spend` run,
replace with pass@1 per host (same model, pinned provider). A task
that Flash passes on every host gets dropped a band; 0/8 stays
`very_hard` or gets rewritten.

`utc_lookback` is `med` (not `easy`) because the test freezes two
clocks; `date.today()` still looks right if you do not split TZ.

Source of truth: `catalog.py`.
