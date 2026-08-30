# data-pipeline-eval

Public gym for data-pipeline incidents. Generic lakehouse, not a
product dump. Names are directory ids. **Category** clusters them;
**difficulty** is estimated (`docs/TAXONOMY.md`). Catalog:
`catalog.py`. Fifteen tasks. Anyone can clone and grade.

| Task | Category | Difficulty | Suite |
|---|---|---|---|
| `schema_infer` | schema | med | default |
| `unique_probe` | incremental | hard | default |
| `latest_pointer` | serving | hard | default |
| `occ_retry` | concurrency | hard | default |
| `watermark_poison` | serving | very_hard | default |
| `entity_reload` | incremental | very_hard | default |
| `frozen_basis` | incremental | very_hard | default |
| `read_write_split` | incremental | very_hard | default |
| `mtime_skip` | serving | very_hard | default |
| `rebuild_wipe` | incremental | very_hard | default |
| `drop_resurrect` | serving | very_hard | default |
| `field_readd` | schema | very_hard | default |
| `late_event_close` | time | very_hard | default |
| `timestamptz_cutoff` | schema | easy | calibration |
| `utc_lookback` | time | med | calibration |

Practice tests (`tasks/<id>/tests`) and adjudication tests
(`tasks/<id>/tests_adjudication`) are public. Official candidate
messages omit both. Gold is the un-faulted `warehouse/` tree.
Explanations live in `docs/solutions/` as prose. Comparable rows
need a full `benchmark_repo_sha`, `grader_source_sha`, immutable
grader image digest, prompt hash, and `environment_sha256`.

## Replicate with one OpenRouter key

```sh
git clone https://github.com/Evan-Kim2028/data-pipeline-eval.git
cd data-pipeline-eval
python -m pip install --require-hashes -r requirements.lock
export OPENROUTER_API_KEY=sk-or-...   # or a one-line .env
python verify.py                      # local, no spend
python run_providers.py --spend --smoke
```

`--smoke` is one easy task on z-ai and novita. Request bodies match
except `provider.only` (temp 0, effort high, no fallbacks). Scale:

```sh
python run_providers.py --spend --variance -k 1 --providers z-ai,novita
python run_providers.py --spend --variance -k 5 --providers z-ai,novita,deepinfra,gmicloud,fireworks
```

Each run writes `logs/runs/<id>.jsonl` (gitignored) and
`logs/runs/<id>/LAST_RUN.md`. Resume without re-spend:
`--spend --continue-run <id>`. Turn a jsonl into tables with
`python scripts/write_findings.py <jsonl> --out <dir>`. Harness lock:
`docs/HARNESS.md`.

## Official campaign (frozen pins)

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

`--spend` is required for provider calls. Frozen campaigns pin the
public clone, grader image, and prompt hashes. Resume regrades a saved
`ResponseArtifact` without another request.
