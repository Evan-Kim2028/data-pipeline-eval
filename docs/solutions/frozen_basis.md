# Gold: frozen_basis (very hard)

**Symptom.** First load, existing snapshot is empty. Each incoming
chunk still calls `unique()` against that empty basis. unique still
plans a full dedupe.

**Trap.** `merge_always_unique` is the merge used once a basis
exists. Using it on `[]` is the hang. Comment-free sibling in
`incremental/basis.py`.

**Gold.** If `existing` is empty, return `incoming` and do not call
`unique_fn`. Overlay: `solutions/frozen_basis/app/basis.py`.

**Also green.** Unique the incoming chunk against itself with a
cheap in-memory set, never the planner unique. Tests spy
`unique_fn` and fail if it is called on first load.
