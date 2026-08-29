# Gold: mtime_skip (very hard)

**Symptom.** Crash after the newest chunk lands. Next run compares
input mtime to the output file mtime and skips older unread files.

**Trap.** `pending_by_mtime` is the cheap skip. Output mtime moving
is not a cursor. `processed_names` is the cursor.

**Gold.** Pending = names not in `processed_names`. Overlay:
`warehouse/app/serving_cursors.py`.

Canonical file: `warehouse/warehouse/serving_cursors.py`.
Fault overlay: `tasks/mtime_skip/fault/warehouse/serving_cursors.py`.
Gold diff: `python scripts/audit_tasks.py --task mtime_skip --show-gold-diff`.
