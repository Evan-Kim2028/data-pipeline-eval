# Gold: latest_pointer (hard)

**Symptom.** 90-day backfill wrote partitions newest→oldest and
refreshed `latest` each day. Job green. Serving read the oldest day
as today.

**Trap.** `write_latest` is correct for the **daily** job
(`daily.py`). Backfill reused it “so serving never sees a hole.”
`serve.py` trusts `latest_as_of`.

**Gold.** Backfill writes day partitions only. Do not call
`write_latest`.

Canonical file: `warehouse/warehouse/history/backfill.py`.
Fault overlay: `tasks/latest_pointer/fault/warehouse/history/backfill.py`.
Gold diff: `python scripts/audit_tasks.py --task latest_pointer --show-gold-diff`.
