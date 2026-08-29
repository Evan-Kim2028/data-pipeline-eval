# Gold: rebuild_wipe (very hard)

**Symptom.** Retry after a mid-chunk crash clears staging, so the
rebuild starts at record one and double-applies the prefix.

**Trap.** `restart` is the operator full-rebuild path. `next_chunk`
must not call it on retry. `last_ok` is the checkpoint.

**Gold.** If `last_ok` is None, return 0. Else persist `last_ok` and
return `last_ok + 1`. Overlay: `solutions/rebuild_wipe/app/rebuild.py`.

**Also green.** Copy last_ok into a new staging dict; do not
`.clear()`. Tests: last_ok=3 → 4, `scratch` key survives.
