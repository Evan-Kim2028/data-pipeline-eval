# data-pipeline-eval

Public gym for data-pipeline incidents. Generic lakehouse, not a
product dump. Names are directory ids. **Category** clusters them;
**difficulty** is estimated (`docs/TAXONOMY.md`). Catalog:
`harness/catalog.py`. Fifteen tasks. Anyone can clone and grade.

| Category | What the incident is about |
|---|---|
| `schema` | Inferred dtypes, warehouse binders, mixed ids in one batch. |
| `time` | Which clock the job uses for lookbacks and cutoffs. |
| `incremental` | Cheap emptiness/skip probes that accidentally plan full work. |
| `serving` | What readers or the next run treat as current or done. |
| `concurrency` | Stale handles, OCC, retry that does not re-read. |

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

Practice tests (`tasks/<id>/tests`) and adjudication tests
(`tasks/<id>/tests_adjudication`) are public. Official candidate
messages omit both. Gold is the un-faulted `warehouse/` tree.
Explanations live in `docs/solutions/` as prose.

## Install (no spend)

Python 3.14.3 (`.python-version`). `verify.py` warns if the running
interpreter does not match. Local pytest. No Docker or API key.

```sh
git clone https://github.com/Evan-Kim2028/data-pipeline-eval.git
cd data-pipeline-eval
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python verify.py
```

Each task is red on the fault overlay and green after the gold patch.
`python verify.py --validate-catalog` only checks the catalog and
checkouts.

## Replicate a host bake-off

Needs an OpenRouter key. `--spend` is required for provider calls.

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
`logs/runs/<id>/LAST_RUN.md`. Resume without re-spend:
`--spend --continue-run <id>`. Turn a jsonl into tables with
`python scripts/write_findings.py <jsonl> --out <dir>`. Harness lock:
`docs/HARNESS.md`.

Comparable published rows need a full `benchmark_repo_sha`,
`grader_source_sha`, immutable grader image digest, prompt hash, and
`environment_sha256`.

## Layout

Root CLIs are `verify.py`, `run_providers.py`, `grade.py`, and
`report.py`. Library code is `harness/`. `grade.py` uses the pinned
Docker image (`docs/DOCKER.md`).

## Official campaign (frozen pins)

`grade.py` needs the pinned Docker image.

```sh
python scripts/setup_eval.py --seed 42
python verify.py --validate-catalog
python scripts/audit_tasks.py
python run_providers.py --check-prompts
python run_providers.py --campaign campaigns/official-v1.json --plan
python run_providers.py --campaign campaigns/official-v1.json --preflight
python grade.py --response saved-response.json
python report.py --manifest campaigns/official-v1.json --trials results/official-v1/trials.jsonl --out reports/official-v1
python report.py --manifest campaigns/official-v1.json --trials results/official-v1/trials.jsonl --out reports/official-v1 --check
python scripts/check_release.py
```

Frozen campaigns pin the public clone, grader image, and prompt
hashes. `--resume` regrades a saved `ResponseArtifact` without
another request.
