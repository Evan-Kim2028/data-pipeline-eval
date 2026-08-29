# Gold: watermark_poison (very hard)

**Symptom.** Nightly walks windows and watermarks as it goes. Abort
mid-loop: watermark already past the failed window. Next nightly
skips it (retry poison).

**Trap.** `nightly.py` sets the store **then** `commit`. Comment
says this avoids redoing finished work. `windows.upcoming` is
correct. `metrics.py` is unused.

**Gold.** `commit(w)` then `store.set(w)`. Overlay:
`solutions/watermark_poison/app/nightly.py`.

**Also green.** Try/finally that only sets on success. Tests: after
a raise on `2026-05-03`, watermark is `2026-05-02`.
