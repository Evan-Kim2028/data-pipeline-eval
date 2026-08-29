# Gold solutions

Each default task has:

- Gold code lives in `warehouse/` (the un-faulted monorepo).
- `tasks/<id>/fault/` is the production bug overlay (`python verify.py`).
- `docs/solutions/<task>.md` — what broke, the trap, the gold patch,
  and which other patches still count.
- `solutions/` keeps the gold file copies for the write-ups.

Categories and difficulty bands: `docs/TAXONOMY.md`, `catalog.py`.
