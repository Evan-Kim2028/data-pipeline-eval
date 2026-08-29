# Gold: frozen_basis (very hard)

**Symptom.** First load, existing snapshot is empty. Each incoming
chunk still calls `unique()` against that empty basis. unique still
plans a full dedupe.

**Trap.** `merge_always_unique` is the merge used once a basis
exists. Using it on `[]` is the hang. Comment-free sibling in
`incremental/basis.py`.

**Gold.** If `existing` is empty, return `incoming` and do not call
`unique_fn`.

Canonical file: `warehouse/warehouse/incremental/basis.py`.
Fault overlay: `tasks/frozen_basis/fault/warehouse/incremental/basis.py`.
Gold diff: `python scripts/audit_tasks.py --task frozen_basis --show-gold-diff`.
