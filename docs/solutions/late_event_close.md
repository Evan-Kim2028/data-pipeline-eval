# Gold: late_event_close (very hard)

**Symptom.** Event-time window closed when `processing_at` passed
the window end. A fact with `event_at` in-window arrived the next
day and vanished.

**Trap.** `in_processing_window` is the completeness watermark, not
membership. `closed_processing_at` is unused on the gold path.
Membership is `event_at`.

**Gold.** Keep rows with `start <= event_at <= end`. Overlay:
`warehouse/app/event_time.py`.

Canonical file: `warehouse/warehouse/event_time.py`.
Fault overlay: `tasks/late_event_close/fault/warehouse/event_time.py`.
Gold diff: `python scripts/audit_tasks.py --task late_event_close --show-gold-diff`.
