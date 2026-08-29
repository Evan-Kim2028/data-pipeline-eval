# Gold: latest_pointer (hard)

**Symptom.** 90-day backfill wrote partitions newest→oldest and
refreshed `latest` each day. Job green. Serving read the oldest day
as today.

**Trap.** `write_latest` is correct for the **daily** job
(`daily.py`). Backfill reused it “so serving never sees a hole.”
`serve.py` trusts `latest_as_of`.

**Gold.** Backfill writes day partitions only. Do not call
`write_latest`. Overlay: `solutions/latest_pointer/app/backfill.py`.

**Also green.** Pass a flag `update_latest=False`; restore latest to
the pre-seeded today after the loop. Tests: pointer stays today,
all 90 keys exist.
