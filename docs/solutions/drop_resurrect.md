# Gold: drop_resurrect (very hard)

**Symptom.** Catalog drop of `gold.events`. Next writer
`get_or_create` recreates an empty table. Readers see a live name
with none of the dropped rows.

**Trap.** `create` already refuses tombstones. `get_or_create` skips
`create` and inserts into `tables` directly, discarding the
tombstone.

**Gold.** `get_or_create` must go through `create` (or raise on
tombstone). Overlay: `solutions/drop_resurrect/app/lifecycle.py`.

**Also green.** Explicit `if name in tombstones: raise`. Tests:
open_for_write after drop raises `dropped:gold.events`.
