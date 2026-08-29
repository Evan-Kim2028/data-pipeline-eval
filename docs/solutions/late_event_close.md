# Gold: late_event_close (very hard)

**Symptom.** Event-time window closed when `processing_at` passed
the window end. A fact with `event_at` in-window arrived the next
day and vanished.

**Trap.** `in_processing_window` is the completeness watermark, not
membership. `closed_processing_at` is unused on the gold path.
Membership is `event_at`.

**Gold.** Keep rows with `start <= event_at <= end`. Overlay:
`solutions/late_event_close/app/event_time.py`.

**Also green.** Separate a lateness buffer; do not drop on
processing close. Tests: `ent-000-late` stays in yesterday's window
when processing closed yesterday.
