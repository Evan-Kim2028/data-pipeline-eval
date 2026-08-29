# Gold: rebuild_wipe (very hard)

**Symptom.** Retry after a mid-chunk crash clears staging, so the
rebuild starts at record one and double-applies the prefix.

**Trap.** `restart` is the operator full-rebuild path. `next_chunk`
must not call it on retry. `last_ok` is the checkpoint.

**Gold.** If `last_ok` is None, return 0. Else persist `last_ok` and
return `last_ok + 1`.

Canonical file: `warehouse/warehouse/incremental/rebuild.py`.
Fault overlay: `tasks/rebuild_wipe/fault/warehouse/incremental/rebuild.py`.
Gold diff: `python scripts/audit_tasks.py --task rebuild_wipe --show-gold-diff`.
