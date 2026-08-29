# Gold: field_readd (very hard)

**Symptom.** Drop column `note`, re-add as int. Historical string
values appear in the new column because the writer reused the
dropped field id.

**Trap.** Caching dropped `(id, type)` looks like a friendly
revert. Iceberg-style identity reuse is the leak. `add_field`
assigns a new id; `readd_field` must call it.

**Gold.** `readd_field` → `add_field` (new identity). Old rows stay
keyed by the old id. Overlay: `solutions/field_readd/app/schema_evo.py`.

**Also green.** Rename-on-drop then add. Tests: `"legacy"` not in
`read_column("note")` after readd; `7` is.
