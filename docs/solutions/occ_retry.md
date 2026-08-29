# Gold: occ_retry (hard)

**Symptom.** CommitConflict on a stale handle. Retry used the same
in-memory table, so every attempt conflicted.

**Trap.** Comment in `retry.py` says do not refresh *before the
first* attempt (true) and then never refreshes at all (false).
`table.py` / `publish.py` / `backfill.py` are fine.

**Gold.** On `CommitConflict`, `table.refresh()` then retry. Do not
refresh before attempt 1. Do not retry `ValueError`. Overlay:
`solutions/occ_retry/app/retry.py`.

**Also green.** Refresh only after a conflict; cap attempts; last
conflict re-raised.
