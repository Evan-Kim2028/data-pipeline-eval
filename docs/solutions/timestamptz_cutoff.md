# Gold: timestamptz_cutoff (calibration)

**Symptom.** `event_at` is timestamptz. Cutoff was `date.isoformat()`
→ `ValueError: Invalid timestamp with zone: YYYY-MM-DD`.

**Gold.** Return midnight UTC datetime with a zone. Overlay:
`warehouse/app/cutoff.py`.

Canonical file: `warehouse/warehouse/sidecar/cutoff.py`.
Fault overlay: `tasks/timestamptz_cutoff/fault/warehouse/sidecar/cutoff.py`.
Gold diff: `python scripts/audit_tasks.py --task timestamptz_cutoff --show-gold-diff`.
