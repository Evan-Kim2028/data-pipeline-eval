# Gold solutions

`warehouse/` holds the executable gold. Each task replaces one
file in that tree with a broken copy under `tasks/<id>/fault`.
Writeups in this directory are prose.

Generate the official gold unified diff with:

```sh
python scripts/audit_tasks.py --task unique_probe --show-gold-diff
```

`python scripts/audit_tasks.py` checks every catalog task. Both
public test tiers fail on the fault. The generated gold patch
applies strictly and passes. Every registered mutant applies and
fails. Official candidate messages leave these files out.
