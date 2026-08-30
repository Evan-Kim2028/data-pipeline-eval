# Categories and difficulty

Task names are the directory ids (`schema_infer`, and the rest).
Category groups those ids. Difficulty is an estimate until a
scored campaign publishes pass rates. Campaign difficulty is one
minus that task's end-to-end rate. The labels below stay as
estimates until that rate exists.

## Categories

| id | Label | What the incident is about |
|---|---|---|
| `schema` | Schema and types | The job guessed the wrong type for a column. |
| `time` | Time and calendars | The job used the wrong clock. |
| `incremental` | Incremental I/O | The job thought it could skip work and still scanned everything. |
| `serving` | Serving contracts | The next reader, or the next run, treated the wrong thing as current. |
| `concurrency` | Concurrent writers | Two writers. A retry reused a stale table handle. |

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
