# Gold: mtime_skip (very hard)

**Symptom.** Crash after the newest chunk lands. Next run compares
input mtime to the output file mtime and skips older unread files.

**Trap.** `pending_by_mtime` is the cheap skip. Output mtime moving
is not a cursor. `processed_names` is the cursor.

**Gold.** Pending = names not in `processed_names`. Overlay:
`solutions/mtime_skip/app/serving_cursors.py`.

**Also green.** Persist a name set / watermark of processed files.
Tests: output_mtime=90, processed `{chunk-new}` still leaves
chunk-old and chunk-mid pending.
