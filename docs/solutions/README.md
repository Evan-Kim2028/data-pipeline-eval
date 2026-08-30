# Gold solutions

`warehouse/` is the only executable gold. Each task replaces one
file in that tree with a broken copy under `tasks/<id>/fault`.
Writeups in this directory are prose.

Generate the official gold unified diff with:

```sh
python scripts/audit_tasks.py --task unique_probe --show-gold-diff
```

`python scripts/audit_tasks.py` checks every catalog task: both public
test tiers fail on the fault, the generated gold patch applies
strictly and passes, and every registered mutant applies and fails.
Official candidate messages omit these files.
