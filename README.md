# data-pipeline-eval

Fifteen broken lakehouse jobs. The model gets the pager text and
writes a unified diff. Pytest grades the repair. Generic warehouse,
not a product dump.

> ValueError: Invalid timestamp with zone: 2026-07-13
>
> The job never started the scan. Sidecar is behind.

That one is `timestamptz_cutoff`. The other fourteen are the same
shape: a real incident, a small edit, a hidden test that catches
the almost-right patch.

## Try it

Python 3.14.3 (`.python-version`). `verify.py` warns if you are on
something else.

```sh
git clone https://github.com/Evan-Kim2028/data-pipeline-eval.git
cd data-pipeline-eval
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python verify.py
```

Every task should fail on `tasks/<id>/fault` and pass after the
gold patch. Then, with an OpenRouter key (`--spend` calls a host):

```sh
export OPENROUTER_API_KEY=sk-or-...   # or a one-line .env
python run_providers.py --spend --smoke
```

`--smoke` is that timestamptz bug on z-ai and novita. Same request
body except `provider.only` (temp 0, effort high, no fallbacks).

```sh
python run_providers.py --spend --variance -k 1 --providers z-ai,novita
python run_providers.py --spend --variance -k 5 --providers z-ai,novita,deepinfra,gmicloud,fireworks
```

Runs land in `logs/runs/<id>.jsonl`. Resume with
`--spend --continue-run <id>`. Tables:
`python scripts/write_findings.py <jsonl> --out <dir>`.
Lock: `docs/HARNESS.md`. Catalog: `harness/catalog.py`.

## The fifteen tasks

Five kinds of break, then easy → very hard. `calibration` is two
warm-ups. `default` is the rest. Difficulty is an estimate
(`docs/TAXONOMY.md`).

| Kind | What breaks |
|---|---|
| `schema` | Guessed types. A date sent as timestamptz. Mixed ids in one load. |
| `time` | The job used the wrong clock. |
| `incremental` | A cheap skip check that still plans a full scan. |
| `serving` | Readers, or the next run, treat the wrong thing as current. |
| `concurrency` | Stale table handle. Retry that does not re-read. |

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

Practice tests: `tasks/<id>/tests`. Second suite:
`tasks/<id>/tests_adjudication`. Both public, both grade, neither
goes in the official prompt. Gold is `warehouse/`. Writeups:
`docs/solutions/`.
