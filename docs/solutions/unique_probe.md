# Gold: unique_probe (hard)

**Symptom.** Emptiness probe uniqued the delta, then `limit(1)`. The
unique was still a full plan. Job hung after staging, no merge.

**Trap.** Comment in `probe.py` claims unique+limit is cheap.
`merge.py` is clean. The spy scan raises `MemoryError` on `.unique()`.

**Gold.** Probe the **un-deduped** scan: `limit(1).collect().height`.
Overlay: `solutions/unique_probe/app/probe.py`.

**Also green.** `collect().height` without unique; any probe that
never calls `unique()`. Dedup belongs on a *second* scan after you
know there are rows — not in this function.
