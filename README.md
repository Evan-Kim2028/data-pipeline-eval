# data-pipeline-eval

I run a lakehouse. Models I tried kept missing the same pipeline
repairs, so I turned those failures into a public eval.

Each task is a broken scheduled job. It reads files and writes
tables. The model reads the incident and answers with a unified
diff. Tests decide whether the repair works. The warehouse is
generic. I have hit these bugs at work.

## The fifteen tasks

> ValueError: Invalid timestamp with zone: 2026-07-13
>
> The job never started the scan. Sidecar is behind.

Start with `timestamptz_cutoff`. The cutoff is a Python `date`.
The column is a timestamp with a time zone. The broken code
returns `cutoff.isoformat()`, the string `2026-07-13`, and the
job raises. Read these four files in order:

1. `tasks/timestamptz_cutoff/prompt.txt`
2. `tasks/timestamptz_cutoff/fault/warehouse/sidecar/cutoff.py`
3. `tasks/timestamptz_cutoff/tests/test_scan.py`
4. `docs/solutions/timestamptz_cutoff.md`

The other fourteen tasks use the same four-file shape. A second
test suite under `tasks/<id>/tests_adjudication` fails a patch
that only fixes the happy path. Official prompts include the
incident and the production files. Gold code lives in
`warehouse/`.

| Kind | What breaks |
|---|---|
| `schema` | Wrong type on a column. |
| `time` | Wrong clock. |
| `incremental` | A skip check that still scanned everything. |
| `serving` | The next reader treated the wrong thing as current. |
| `concurrency` | A retry reused a stale table handle. |

Tasks are grouped by that kind and ordered from easy to very
hard. `calibration` is two warm-ups. `default` is the other
thirteen. Difficulty is an estimate. See `docs/TAXONOMY.md`.

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
