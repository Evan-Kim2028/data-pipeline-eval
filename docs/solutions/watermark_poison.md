# Gold: watermark_poison (very hard)

**Symptom.** Nightly walks windows and watermarks as it goes. Abort
mid-loop: watermark already past the failed window. Next nightly
skips it (retry poison).

**Trap.** `nightly.py` sets the store **then** `commit`. Comment
says this avoids redoing finished work. `windows.upcoming` is
correct. `metrics.py` is unused.

**Gold.** `commit(w)` then `store.set(w)`. Overlay:
`warehouse/app/nightly.py`.

Canonical file: `warehouse/warehouse/checkpoints/nightly.py`.
Fault overlay: `tasks/watermark_poison/fault/warehouse/checkpoints/nightly.py`.
Gold diff: `python scripts/audit_tasks.py --task watermark_poison --show-gold-diff`.
