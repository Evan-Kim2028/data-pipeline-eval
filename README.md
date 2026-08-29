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
| `timestamptz_cutoff` | schema | easy | calibration |
| `utc_lookback` | time | med | calibration |

Fixtures are synthetic jsonl. Ingest is local files only.

Incidents sit in a shared `warehouse/` tree (ingest/silver/gold/catalog/
history/ops/sources). Each task applies a one-file `fault/` overlay.
Hidden tests grade the failure mode. Gold is the un-faulted tree plus
`docs/solutions/`. Python in `warehouse/` and `tasks/` has no inline
comments; docs stay in `docs/`.

```sh
python verify.py                 # starters red, gold overlays green
python run_providers.py          # refuses OpenRouter until --spend
```
