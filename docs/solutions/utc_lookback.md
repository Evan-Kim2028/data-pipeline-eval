# Gold: utc_lookback (calibration)

**Symptom.** Lookback used `date.today()` (host calendar). Warehouse
dates are UTC. Around midnight they disagree by a day.

**Gold.** Anchor on `utc_today()` (`datetime.now(timezone.utc).date()`).
Overlay: `warehouse/app/lookback.py`.

Canonical file: `warehouse/warehouse/time/lookback.py`.
Fault overlay: `tasks/utc_lookback/fault/warehouse/time/lookback.py`.
Gold diff: `python scripts/audit_tasks.py --task utc_lookback --show-gold-diff`.
