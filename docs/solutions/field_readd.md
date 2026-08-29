# Gold: field_readd (very hard)

**Symptom.** Drop column `note`, re-add as int. Historical string
values appear in the new column because the writer reused the
dropped field id.

**Trap.** Caching dropped `(id, type)` looks like a friendly
revert. Iceberg-style identity reuse is the leak. `add_field`
assigns a new id; `readd_field` must call it.

**Gold.** `readd_field` → `add_field` (new identity). Old rows stay
keyed by the old id.

Canonical file: `warehouse/warehouse/schema_evo.py`.
Fault overlay: `tasks/field_readd/fault/warehouse/schema_evo.py`.
Gold diff: `python scripts/audit_tasks.py --task field_readd --show-gold-diff`.
