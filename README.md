# data-pipeline-eval

This repository is a public eval of fifteen broken lakehouse jobs.
The model reads the incident text and writes a unified diff. Pytest
grades the repair. The warehouse is a generic lakehouse built for
this eval.

> ValueError: Invalid timestamp with zone: 2026-07-13
>
> The job never started the scan. Sidecar is behind.

`timestamptz_cutoff` is the easy example. The other fourteen tasks
follow the same shape. Each one is a real incident, a small edit,
and a second test suite that fails an almost-right patch.

## Try it

The pinned interpreter is Python 3.14.3 (`.python-version`).
`verify.py` prints a warning when the running interpreter differs.

```sh
git clone https://github.com/Evan-Kim2028/data-pipeline-eval.git
cd data-pipeline-eval
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python verify.py
```

`verify.py` fails each task on the broken files in `tasks/<id>/fault`
and passes it after the gold patch.

An OpenRouter key is required to call a host. Pass `--spend` when
you want provider calls.

```sh
export OPENROUTER_API_KEY=sk-or-...   # or a one-line .env
python run_providers.py --spend --smoke
```

`--smoke` runs `timestamptz_cutoff` on z-ai and novita. Request
bodies match except `provider.only`. Sampling stays at temperature
0 with high effort and fallbacks disabled.

These commands scale the same setup:

```sh
python run_providers.py --spend --variance -k 1 --providers z-ai,novita
python run_providers.py --spend --variance -k 5 --providers z-ai,novita,deepinfra,gmicloud,fireworks
```

Each run writes `logs/runs/<id>.jsonl`. Resume an incomplete run
with `--spend --continue-run <id>`. Build tables with
`python scripts/write_findings.py <jsonl> --out <dir>`. The request
lock is `docs/HARNESS.md`. The catalog is `harness/catalog.py`.

## The fifteen tasks

Tasks are grouped by kind of incident and ordered from easy to
very hard. The `calibration` suite is two warm-up tasks. The
`default` suite is the other thirteen. Difficulty is an estimate.
See `docs/TAXONOMY.md`.

| Kind | What breaks |
|---|---|
| `schema` | Guessed types. A date sent as timestamptz. Mixed ids in one load. |
| `time` | The job used the wrong clock. |
| `incremental` | A cheap skip check that still plans a full scan. |
| `serving` | Readers, or the next run, treat the wrong thing as current. |
| `concurrency` | A stale table handle. A retry that reuses it. |

| Task | Kind | Difficulty | Suite |
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

Practice tests live in `tasks/<id>/tests`. A second suite lives in
`tasks/<id>/tests_adjudication`. Both directories are public and
both run at grade time. Official prompts include the incident and
production files. Gold code lives in `warehouse/`. Prose writeups
live in `docs/solutions/`.
