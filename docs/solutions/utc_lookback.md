# Gold: utc_lookback (calibration)

**Symptom.** Lookback used `date.today()` (host calendar). Warehouse
dates are UTC. Around midnight they disagree by a day.

**Gold.** Anchor on `utc_today()` (`datetime.now(timezone.utc).date()`).
Overlay: `solutions/utc_lookback/app/lookback.py`.
