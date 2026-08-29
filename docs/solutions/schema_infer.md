# Gold: schema_infer (med)

**Symptom.** One jsonl batch: first hundred `listing_id` values are
digits, then a UUID. Load crashes on `int(...)`.

**Trap.** `infer_listing_id_kind` samples `INFER_SAMPLE` (100) and
returns `int`. `coerce.as_ids` applies that kind to the whole batch.
`legacy.py` is a second head sample and is not on the nightly path.

**Gold.** Infer from the **full** batch (or always treat ids as
strings). Overlay: `solutions/schema_infer/app/schema.py`.

**Also green.** Force `kind = str`; set `INFER_SAMPLE` to `None` and
honor it; raise a typed error only after scanning all rows — tests
only require no crash and string ids.
