# Gold: read_write_split (very hard)

**Symptom.** Partition overwrite writes `bronze[day]`. The following
read walks every partition and returns the union.

**Trap.** `read_all` is the flatten helper for audits. `read_day`
must not call it. Write path is already keyed.

**Gold.** `read_day` returns `bronze.get(day, [])` only. Overlay:
`warehouse/app/partition_io.py`.

Canonical file: `warehouse/warehouse/incremental/partition_io.py`.
Fault overlay: `tasks/read_write_split/fault/warehouse/incremental/partition_io.py`.
Gold diff: `python scripts/audit_tasks.py --task read_write_split --show-gold-diff`.
