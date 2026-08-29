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

Fixtures are synthetic jsonl (`entity_id` / `event_at` / `amount` /
`source`). Ingest is local files only. Same seed rebuilds them.

Incidents sit in a shared `warehouse/` tree (ingest/silver/gold/catalog/
history/ops/sources). Each task applies a one-file `fault/` overlay.
Hidden tests grade the failure mode. Gold is the un-faulted tree plus
`docs/solutions/`. Python in `warehouse/` and `tasks/` has no inline
comments; docs stay in `docs/`.

```sh
python scripts/setup_eval.py --seed 42    # synthetic jsonl + partitions
python verify.py                          # starters red, gold green
python run_providers.py                   # refuses OpenRouter until --spend
```
