# Categories and difficulty

Task names are the directory ids (`schema_infer`, and the rest).
Category groups those ids. Difficulty is an estimate until a
scored campaign publishes pass rates. Campaign difficulty is one
minus that task's end-to-end rate. The labels below stay as
estimates until that rate exists.

## Categories

| id | Label | What the incident is about |
|---|---|---|
| `schema` | Schema and types | Guessed column types, a date sent as timestamptz, mixed ids |
| `time` | Time and calendars | Host clock versus warehouse dates |
| `incremental` | Incremental I/O | Cheap skip checks that still plan a full scan |
| `serving` | Serving contracts | What readers or the next run treat as current |
| `concurrency` | Concurrent writers | Stale handles. Optimistic-concurrency retry |

## Difficulty (estimated)

These levels assume a one-shot unified diff, no tools, a messy
production tree, and public tests left out of the candidate
message.

| Level | Means |
|---|---|
| `easy` | The causal line is in the module the prompt points at. One invariant. |
| `med` | The model must pick the right file among distractors. Equivalent gold patches exist. |
| `hard` | A correct helper is used in the wrong place, or a comment lies about cost. |
| `very_hard` | Ordering matters. A patch that only satisfies the happy path fails the abort test. |

The catalog in `harness/catalog.py` is the source of these labels.
