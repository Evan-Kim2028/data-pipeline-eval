# Gold: timestamptz_cutoff (calibration)

**Symptom.** `event_at` is timestamptz. Cutoff was `date.isoformat()`
→ `ValueError: Invalid timestamp with zone: YYYY-MM-DD`.

**Gold.** Return midnight UTC datetime with a zone. Overlay:
`solutions/timestamptz_cutoff/app/cutoff.py`.
