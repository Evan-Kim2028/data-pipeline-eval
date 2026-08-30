# data-pipeline-eval

Public gym for data-pipeline incidents. Generic lakehouse, not a
product dump. Names are directory ids. **Category** clusters them;
**difficulty** is estimated (`docs/TAXONOMY.md`). Catalog:
`harness/catalog.py`. Fifteen tasks.

| Category | What the incident is about |
|---|---|
| `schema` | Guessed column types, a date sent as timestamptz, mixed ids in one load. |
| `time` | Which clock the job uses for lookbacks and cutoffs. |
| `incremental` | Cheap skip checks that still plan a full scan. |
| `serving` | What readers or the next run treat as current or done. |
| `concurrency` | Stale table handles. Optimistic-concurrency retry that does not re-read. |

| Task | Category | Difficulty | Suite |
|---|---|---|---|
| `timestamptz_cutoff` | schema | easy | calibration |
| `schema_infer` | schema | med | default |
| `field_readd` | schema | very_hard | default |
| `utc_lookback` | time | med | calibration |
| `late_event_close` | time | very_hard | default |
| `unique_probe` | incremental | hard | default |
| `entity_reload` | incremental | very_hard | default |
| `frozen_basis` | incremental | very_hard | default |
| `read_write_split` | incremental | very_hard | default |
| `rebuild_wipe` | incremental | very_hard | default |
| `latest_pointer` | serving | hard | default |
| `watermark_poison` | serving | very_hard | default |
| `mtime_skip` | serving | very_hard | default |
| `drop_resurrect` | serving | very_hard | default |
| `occ_retry` | concurrency | hard | default |

Each task has practice tests in `tasks/<id>/tests` and a second
suite in `tasks/<id>/tests_adjudication`. Both are public and both
run at grade time. Official prompts include neither. Gold is the
working `warehouse/` tree. Writeups are `docs/solutions/`.

## Install

Python 3.14.3 (`.python-version`). `verify.py` warns if the running
interpreter does not match.

```sh
git clone https://github.com/Evan-Kim2028/data-pipeline-eval.git
cd data-pipeline-eval
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python verify.py
```

Each task fails on the broken files in `tasks/<id>/fault` and
passes after the gold patch. `python verify.py --validate-catalog`
only checks the catalog and task files.

## Replicate

```sh
export OPENROUTER_API_KEY=sk-or-...   # or a one-line .env
python run_providers.py --spend --smoke
```

`--smoke` is `timestamptz_cutoff` on z-ai and novita. Request bodies
match except `provider.only` (temp 0, effort high, no fallbacks).
Scale:

```sh
python run_providers.py --spend --variance -k 1 --providers z-ai,novita
python run_providers.py --spend --variance -k 5 --providers z-ai,novita,deepinfra,gmicloud,fireworks
```

Each run writes `logs/runs/<id>.jsonl` (gitignored) and
`logs/runs/<id>/LAST_RUN.md`. Resume an incomplete run with
`--spend --continue-run <id>`. Tables:
`python scripts/write_findings.py <jsonl> --out <dir>`.
Request lock: `docs/HARNESS.md`.
