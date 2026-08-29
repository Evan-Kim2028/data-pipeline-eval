# Gold: entity_reload (very hard)

**Symptom.** Watermark lists changed entity keys. The event scan
keeps those keys but drops `event_at >= since`, so each changed
entity reloads its full history.

**Trap.** `load_all_for_ids` is the full-history helper and looks
like the nightly path. `jobs.entity_reload.changed_ids` is already
correct. The scan in `load_changed` is the one that lost `since`.

**Gold.** Filter `entity_id in changed_ids` **and** `event_at >=
since`. Overlay: `solutions/entity_reload/app/reload.py`.

**Also green.** Intersect with a watermarked slice first, then
filter keys. Tests: `len(rows) < 20` and every row `event_at >= since`.
