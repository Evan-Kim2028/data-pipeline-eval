# Gold: read_write_split (very hard)

**Symptom.** Partition overwrite writes `bronze[day]`. The following
read walks every partition and returns the union.

**Trap.** `read_all` is the flatten helper for audits. `read_day`
must not call it. Write path is already keyed.

**Gold.** `read_day` returns `bronze.get(day, [])` only. Overlay:
`solutions/read_write_split/app/partition_io.py`.

**Also green.** Re-read the key just written; skip a glob of `*`.
Tests: overwrite 2026-08-01 must not surface 2026-08-02.
