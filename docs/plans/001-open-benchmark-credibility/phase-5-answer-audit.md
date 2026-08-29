# Phase 5: Audit answers and keep one gold tree

[Back to the overview](./overview.md)

## Goal

Make `warehouse/` the only executable gold answer. Keep public explanations in `docs/solutions/`, but remove copied solution code and unproved alternative-answer claims. Add one deterministic audit that proves every task has valid tests, a red fault, a strictly applicable green gold patch, consistent public documentation, and rejected known-wrong patches.

## Dependencies

- Phase 1 has landed validated `TaskSpec` records in `catalog.py`.
- Phase 2 has landed `prompt_bundle.py`, prompt snapshots, and candidate messages that exclude public tests and explanations.
- Phase 3 has landed `patches.py` as the only strict patch path.
- The public grader phase has one seed and pytest path behind `verify.py`. The audit must call those paths rather than copy them.
- Start from a green public feature branch with no uncommitted changes.

## Changes

- Delete all 15 copied implementations under `solutions/<task>/app/*.py`. Delete the empty `solutions/` tree. Do not replace the copies with symlinks.
- Rename each public `tasks/<id>/tests_held/` directory to `tasks/<id>/tests_adjudication/`. Keep `tasks/<id>/tests/` as readable practice checks. Both tiers remain public and both run during official grading. Official candidate messages include neither tier.
- Update `docs/solutions/README.md` to state that `warehouse/` is the sole code gold. Explain how to generate a task's unified gold diff through `scripts/audit_tasks.py`.
- Rewrite every `docs/solutions/<task>.md` as prose. Point to the canonical `warehouse/` file and the public fault file. Remove every `Also green` section and every equivalent-answer claim that no registered test and mutant prove.
- Update `README.md`, `docs/HARNESS.md`, and `docs/TAXONOMY.md`. Replace hidden-test language with the public contract. Tests and explanations are public in the clone, but `prompt_bundle.py` omits them from official candidate messages.
- Extend the Phase 1 `TaskSpec` contract in `contracts.py` and its records in `catalog.py` only if they lack a canonical gold path, explanation path, or mutant directory. Keep `catalog.py` as the only task registry. Do not add per-task metadata manifests.
- Add at least one strictly applicable known-wrong patch under each `tasks/<id>/mutants/` directory. Use candidate-style unified diffs. The initial set proves the mutant mechanism. Phase 6 adds the stronger test-evading patches.
- Add `scripts/audit_tasks.py`. Iterate in `catalog.all_ids()` order and use fresh temporary checkouts. Do not use the network, wall-clock values, random order, or absolute paths in output.
- Make `verify.py` a compatibility entry point to the same public grader and audit primitives. Route patch work through `patches.py`. Remove duplicate seed or pytest behavior when the shared grader already owns it.

The answer map is fixed:

| Task | Canonical gold | Public explanation |
|---|---|---|
| `schema_infer` | `warehouse/warehouse/silver/schema.py` | `docs/solutions/schema_infer.md` |
| `unique_probe` | `warehouse/warehouse/gold/probe.py` | `docs/solutions/unique_probe.md` |
| `latest_pointer` | `warehouse/warehouse/history/backfill.py` | `docs/solutions/latest_pointer.md` |
| `occ_retry` | `warehouse/warehouse/catalog/retry.py` | `docs/solutions/occ_retry.md` |
| `watermark_poison` | `warehouse/warehouse/checkpoints/nightly.py` | `docs/solutions/watermark_poison.md` |
| `entity_reload` | `warehouse/warehouse/incremental/reload.py` | `docs/solutions/entity_reload.md` |
| `frozen_basis` | `warehouse/warehouse/incremental/basis.py` | `docs/solutions/frozen_basis.md` |
| `read_write_split` | `warehouse/warehouse/incremental/partition_io.py` | `docs/solutions/read_write_split.md` |
| `mtime_skip` | `warehouse/warehouse/serving_cursors.py` | `docs/solutions/mtime_skip.md` |
| `rebuild_wipe` | `warehouse/warehouse/incremental/rebuild.py` | `docs/solutions/rebuild_wipe.md` |
| `drop_resurrect` | `warehouse/warehouse/lifecycle.py` | `docs/solutions/drop_resurrect.md` |
| `field_readd` | `warehouse/warehouse/schema_evo.py` | `docs/solutions/field_readd.md` |
| `late_event_close` | `warehouse/warehouse/event_time.py` | `docs/solutions/late_event_close.md` |
| `timestamptz_cutoff` | `warehouse/warehouse/sidecar/cutoff.py` | `docs/solutions/timestamptz_cutoff.md` |
| `utc_lookback` | `warehouse/warehouse/time/lookback.py` | `docs/solutions/utc_lookback.md` |

For each task, `scripts/audit_tasks.py` must run these checks in order:

1. Validate the catalog paths, public explanation, fault overlay, canonical gold files, and discovered mutant patches.
2. Collect practice and adjudication tests twice. Require the same nonempty ordered node ids and distinguish collection errors from assertion failures.
3. Seed the official faulted checkout and require pytest exit code 1 from both public tiers. A timeout, import error, no-tests result, or grader error does not count as red.
4. Generate the gold unified diff from the fault overlay and canonical `warehouse/` files. Apply it through the official grader with one declared strip level, zero fuzz, no context-replacement fallback, and an exact allowed-path check.
5. Require the patched checkout to match the canonical gold files byte for byte and pass the task tests.
6. Apply every registered mutant through the same strict path. A mutant counts as rejected only when it applies cleanly and pytest exits 1 for a test failure.
7. Check document and prompt consistency. No executable gold answer may exist outside `warehouse/`. No explanation may reference the deleted `solutions/` tree or say `Also green`. The official rendered prompt path list must exclude tests, explanations, mutants, caches, logs, and results.

## Data structures

- `TaskAuditSpec` is `TaskSpec, practice tests, adjudication tests, ordered fault-to-gold path pairs, explanation path, mutant directory`.
- `PathPair` is `fault path, canonical gold path, checkout-relative target path`.
- `MutantSpec` is `task id, stable filename id, unified-diff path, changed paths`.
- `TaskAuditResult` is `task id, collected node ids, fault outcome, gold-apply outcome, gold outcome, mutant outcomes, document errors`.

The audit derives these values from `catalog.py` and committed paths. It does not maintain a second task list.

## Subagent execution

- The coordinator owns `contracts.py`, `catalog.py`, `patches.py`, `scripts/audit_tasks.py`, `verify.py`, `README.md`, `docs/HARNESS.md`, `docs/TAXONOMY.md`, and `docs/solutions/README.md`.
- Give one isolated worktree exclusive ownership of deleting `solutions/**`.
- Use at most five parallel category worktrees for task-local files. Each owns only its assigned `docs/solutions/<id>.md` and `tasks/<id>/mutants/**` paths.
- Do not let category workers edit prompts, prompt snapshots, grader code, or shared docs. Each worker returns one commit from the agreed Phase 5 base.
- Integrate one commit at a time. Run the full audit after each integration. Return a failing slice to its owner instead of fixing it in a different task's commit.

## Verification

Static checks:

- Run `python -m compileall -q scripts/audit_tasks.py patches.py contracts.py catalog.py verify.py run_providers.py prompt_bundle.py`.
- Run the focused grader, catalog, prompt, and audit tests under `tests/`.
- Run `test ! -d solutions`.
- Run `rg -n "Also green|Overlay: solutions/" docs/solutions` and require no matches.
- Run `git diff --check`.

CLI runtime checks:

- Use `control-cli` to run `python scripts/audit_tasks.py --task unique_probe --show-gold-diff`. Confirm the diff touches only `warehouse/warehouse/gold/probe.py` and applies through the official grader.
- Use `control-cli` to run `python scripts/audit_tasks.py --task unique_probe`. Confirm collection, fault, gold, documentation, and mutant checks report their expected states.
- Run `python scripts/audit_tasks.py --format json` twice and compare the files byte for byte. Require 15 tasks in `catalog.all_ids()` order and no timing or temporary-path drift.
- Run `python verify.py` from a clean clone. Require all 15 faults red, all generated gold patches green, all registered mutants rejected, and exit code zero.
- Run `python run_providers.py --check-prompts` with networking disabled. Require the committed prompt hashes and denied-path checks to remain green.

## Commit and push checkpoint

First commit the deletion and prose-only documentation update. Then commit the audit, baseline mutants, and compatibility wiring. Run `/deslop`, the static checks, and the full CLI audit before each push. Push each green checkpoint to `feature/open-benchmark-credibility`; do not begin Phase 6 from an unpushed commit.

## Exit criteria

- `solutions/` does not exist, and `warehouse/` is the sole executable gold.
- Every explanation points to canonical files or the deterministic generated-diff command. No unproved `Also green` claim remains.
- One public audit checks all 15 tasks in stable order and reports infrastructure errors separately from behavioral red results.
- Every fault is red on both public test tiers, every generated gold patch applies strictly and is green on both, and every registered known-wrong patch applies strictly and is red.
- Official candidate messages still omit public tests, explanations, and mutants.
- A clean public clone reproduces the same zero-exit audit without a private repository or network access.
