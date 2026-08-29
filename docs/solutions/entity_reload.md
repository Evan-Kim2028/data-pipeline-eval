# Gold: entity_reload (very hard)

**Symptom.** Watermark lists changed entity keys. The event scan
keeps those keys but drops `event_at >= since`, so each changed
entity reloads its full history.

**Trap.** `load_all_for_ids` is the full-history helper and looks
like the nightly path. `jobs.entity_reload.changed_ids` is already
correct. The scan in `load_changed` is the one that lost `since`.

**Gold.** Filter `entity_id in changed_ids` **and** `event_at >=
since`.

Canonical file: `warehouse/warehouse/incremental/reload.py`.
Fault overlay: `tasks/entity_reload/fault/warehouse/incremental/reload.py`.
Gold diff: `python scripts/audit_tasks.py --task entity_reload --show-gold-diff`.
