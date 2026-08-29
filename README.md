# data-pipeline-eval

Public gym for data-pipeline incidents. Generic lakehouse, not a
product dump. Names are directory ids. **Category** clusters them;
**difficulty** is estimated (`docs/TAXONOMY.md`). Catalog:
`catalog.py`.

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
| `join_fanout` | transform | hard | default |
| `window_partition` | transform | hard | default |
| `rows_range` | transform | hard | default |
| `calendar_spine` | time | med | default |
| `scd2_close` | serving | very_hard | default |
| `safe_ratio` | transform | med | default |
| `refund_net` | serving | hard | default |
| `late_merge` | incremental | very_hard | default |
| `fifo_cost` | incremental | hard | default |
| `fx_asof` | time | hard | default |
| `book_period` | time | very_hard | default |
| `deferred_prorate` | time | hard | default |

Twelve of those recast mechanisms from Snowflake data-eng-bench
(DuckDB, no account). Harbor is the extra lane for leftover dbt
tasks — see `docs/RELATED.md`.

Fixtures are synthetic jsonl (`entity_id` / `event_at` / `amount` /
`source`). Ingest is local files only. Same seed rebuilds them.

Incidents sit in a shared `warehouse/` tree (ingest/silver/gold/catalog/
history/ops/sources). Each task applies a one-file `fault/` overlay.
Practice tests (`tasks/<id>/tests`) and adjudication tests
(`tasks/<id>/tests_adjudication`) are public. Official candidate messages omit
both. Gold is the un-faulted `warehouse/` tree. Explanations live in
`docs/solutions/` as prose.
Comparable published rows must include a full `benchmark_repo_sha` and
`environment_sha256`. Python in `warehouse/` and `tasks/` has no inline
comments; docs stay in `docs/`.

```sh
python -m pip install --require-hashes -r requirements.lock
python scripts/setup_eval.py --seed 42    # synthetic jsonl + partitions
python verify.py --validate-catalog       # TaskSpec records (catalog.py)
python verify.py                          # starters red, gold green
python scripts/audit_tasks.py             # fault red, gold green, mutants red
python run_providers.py --spend --smoke    # timestamptz_cutoff on z-ai + novita
python run_providers.py --spend --golden   # 5-task ladder on those two hosts
python run_providers.py --spend --hard     # all very_hard tasks on those two hosts
docker build -f docker/grader.Dockerfile -t dpe-grader:dev .
python grade.py --response saved-response.json   # offline regrade, no provider key
```

The public grader image has no network, no provider credentials, and
no host mounts of `warehouse/`. Isolation contains candidate code; it
does not hide public tests at runtime. Comparable rows also record
`grader_source_sha` and the immutable image digest in
`docker/grader-image.json`.
