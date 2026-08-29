# Gold: unique_probe (hard)

**Symptom.** Emptiness probe uniqued the delta, then `limit(1)`. The
unique was still a full plan. Job hung after staging, no merge.

**Trap.** Comment in `probe.py` claims unique+limit is cheap.
`merge.py` is clean. The spy scan raises `MemoryError` on `.unique()`.

**Gold.** Probe the **un-deduped** scan: `limit(1).collect().height`.
Overlay: `warehouse/app/probe.py`.

Canonical file: `warehouse/warehouse/gold/probe.py`.
Fault overlay: `tasks/unique_probe/fault/warehouse/gold/probe.py`.
Gold diff: `python scripts/audit_tasks.py --task unique_probe --show-gold-diff`.
