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

```sh
python -m pip install --require-hashes -r requirements.lock
python scripts/setup_eval.py --seed 42
python verify.py --validate-catalog
python verify.py
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
