# Phase 6: Harden every task against plausible wrong answers

[Back to the overview](./overview.md)

## Goal

Harden all 15 public task graders through the same repeatable loop. Each task gets stronger behavioral invariants and candidate-style wrong-answer patches in one task-only commit. The official grader must reject those patches for the intended reason while the sole gold in `warehouse/` stays green.

## Dependencies

- Phase 5 is pushed and `python scripts/audit_tasks.py` passes from a clean clone.
- `catalog.py` lists all 15 tasks and their canonical gold, public tests, explanations, and mutant directories.
- Official candidate prompt hashes from Phase 2 are green. This phase does not expose tests, explanations, or mutants in candidate messages. Three tasks need an API redesign before fan-out, so their prompt and context changes must repeat the Phase 2 review and snapshot procedure.
- Record the pushed shared-contract and three-task redesign head. Every task-hardening worktree starts from that exact commit.

## Changes

Apply this loop once per task:

1. Add the readable behavioral contract to `tasks/<id>/tests/` and adversarial edge cases to `tasks/<id>/tests_adjudication/`. Prefer observable behavior and direct operation spies over source-text assertions.
2. Add a plausible wrong-answer unified diff under `tasks/<id>/mutants/`. The patch must apply strictly to the faulted checkout and fail because of the new invariant.
3. Run `python scripts/audit_tasks.py --task <id>`. Require valid collection, fault red, gold green, every old mutant red, and the new mutant red.
4. Update only `docs/solutions/<id>.md` when the stronger tests prove a new statement. Keep it prose-only and point to the canonical `warehouse/` path.
5. Commit only that task's two public test tiers, mutants, explanation, and canonical or fault file when the new invariant exposes a real defect there.
6. Cherry-pick the task commit onto the integration branch. Run the full 15-task audit before integrating the next task.

Before task fan-out, redesign `entity_reload`, `frozen_basis`, and `late_event_close` as three sequential units. Each unit may update its canonical and fault code, job wrapper, `TaskSpec` context, prompt, and prompt snapshot. Run the full Phase 2 prompt checks and push each redesign before assigning its test-hardening worker.

For every other task, do not edit `tasks/<id>/prompt.txt` in this phase. If a new invariant contradicts the incident contract, stop that task and return it to the Phase 2 workflow rather than changing a prompt hash inside a grader-only commit.

The required hardening is:

| Task and files | Invariants to prove | Wrong-answer mutants to reject |
|---|---|---|
| `schema_infer`<br>`tasks/schema_infer/tests/test_load.py`<br>`warehouse/warehouse/silver/schema.py` | Infer from the full batch. A numeric head followed by a late UUID returns every id as a string. All-numeric, one-row, and empty batches remain valid. | First-row inference, `INFER_SAMPLE` head inference, and a patch that converts digit strings back to integers. |
| `unique_probe`<br>`tasks/unique_probe/tests/test_merge.py`<br>`warehouse/warehouse/gold/probe.py` | A call-order spy requires `limit(1)` before collection. Collection occurs only on the limited scan. The probe never calls `unique`, `sort`, or unbounded `collect`. Empty and nonempty scans keep their results. | `scan.collect()`, `scan.unique().limit(1)`, and `scan.sort(...).limit(1)`. |
| `latest_pointer`<br>`tasks/latest_pointer/tests/test_backfill.py`<br>`warehouse/warehouse/history/backfill.py` | Backfill writes every historical partition and never writes either latest-pointer key. A write spy must fail on transient pointer writes even when a patch restores today's pointer before returning. Today's payload and pointer remain unchanged. | Write latest on each iteration then restore it, write latest only once at the end, and delete then recreate the pointer. |
| `occ_retry`<br>`tasks/occ_retry/tests/test_publish.py`<br>`warehouse/warehouse/catalog/retry.py` | The trace is commit, then refresh only after `CommitConflict`, then retry. A fresh handle gets no refresh. The last conflict is re-raised at the attempt cap. Unrelated exceptions keep their type and are attempted once. | Catch `Exception` or `ValueError`, refresh before attempt one, retry without refresh, and retry forever after the cap. |
| `watermark_poison`<br>`tasks/watermark_poison/tests/test_nightly.py`<br>`warehouse/warehouse/checkpoints/nightly.py` | Each successful commit persists its checkpoint before the next window starts. A failed commit leaves the last successful checkpoint. A second invocation resumes at the failed window and does not replay earlier committed windows. | Set before commit, set only after the whole loop, and track progress only in a local variable. |
| `entity_reload`<br>`tasks/entity_reload/tests/test_reload.py`<br>`warehouse/warehouse/incremental/reload.py` | Replace list-only filtering with a minimal scan double that records pushed predicates. Require changed-id membership and `event_at >= since` before materialization. Include rows exactly at `since`, reject older rows for changed ids, and reject recent rows for unchanged ids. | Filter by changed id only, filter by time only, compare `changed_at` to `since`, and materialize full history before applying the time predicate. |
| `frozen_basis`<br>`tasks/frozen_basis/tests/test_basis.py`<br>`warehouse/warehouse/incremental/basis.py` | `FirstLoadState` persists ordered rows and seen event ids across multiple incoming chunks. Each chunk uses bounded event-id dedupe and updates current state. The planner `unique_fn` is never called against a frozen empty snapshot. An explicitly supplied nonempty existing basis still follows its declared merge path. | Reinitialize first-load state for each chunk, call planner unique on the empty start snapshot, return duplicate event ids unchanged, reorder first-seen rows, and keep deduplicating against the frozen prior snapshot. |
| `read_write_split`<br>`tasks/read_write_split/tests/test_partition.py`<br>`warehouse/warehouse/incremental/partition_io.py` | A mapping spy forbids global iteration, `.values()`, and `read_all`. The job writes and reads only the requested day. Other partitions and missing-day behavior remain unchanged. | Return the input rows without a keyed read, read all partitions then filter, and return the union of every partition. |
| `mtime_skip`<br>`tasks/mtime_skip/tests/test_cursors.py`<br>`warehouse/warehouse/serving_cursors.py` | Pending files depend only on persisted `processed_names`. A poison `output_mtime` raises on comparison and must remain unused. Older unread, newer unread, empty, and already-processed cases preserve input order without mutating the checkpoint set. | Use output mtime, combine mtime and names with either boolean direction, and replace persisted names with a run-local set. |
| `rebuild_wipe`<br>`tasks/rebuild_wipe/tests/test_rebuild.py`<br>`warehouse/warehouse/incremental/rebuild.py` | Retry persists `last_ok` in the same staging object, preserves unrelated staging keys, and returns `last_ok + 1`. Repeating the call is idempotent. A fresh rebuild with no checkpoint starts at zero without clearing staging. | Clear staging, return the next index without persisting the checkpoint, copy into a detached dictionary, and always restart at zero. |
| `drop_resurrect`<br>`tasks/drop_resurrect/tests/test_lifecycle.py`<br>`warehouse/warehouse/lifecycle.py` | A dropped name remains tombstoned and cannot reopen. A never-seen name still creates a fresh table. Existing live names preserve object identity across repeated opens. | Reject every absent name, discard the tombstone before creation, and return a detached empty table without registering it. |
| `field_readd`<br>`tasks/field_readd/tests/test_schema_evo.py`<br>`warehouse/warehouse/schema_evo.py` | Re-adding a name allocates a new field id and type. Old rows remain stored under the old id but never appear through the new field. Unrelated fields and row history survive the change. | Reuse the dropped id, reset the id counter, clear old rows, and rewrite historical values under the new id. |
| `late_event_close`<br>`tasks/late_event_close/tests/test_window.py`<br>`warehouse/warehouse/event_time.py` | Redesign the toy function into a minimal two-batch window state. Separate event-time membership from processing-time completeness. Accept an in-window late event within the declared lateness policy, upsert by event id, preserve inclusive boundaries, and exclude neighboring days. | Filter membership by `processing_at`, make close permanently freeze membership, duplicate the late event on replay, and accept an event outside the lateness policy. |
| `timestamptz_cutoff`<br>`tasks/timestamptz_cutoff/tests/test_scan.py`<br>`warehouse/warehouse/sidecar/cutoff.py` | Calendar dates at year, month, and leap-day boundaries become exactly midnight with UTC tzinfo and bind successfully as timestamptz. | Return an ISO date string, a naive datetime, local-zone midnight, noon UTC, or the prior day's end. |
| `utc_lookback`<br>`tasks/utc_lookback/tests/test_window.py`<br>`warehouse/warehouse/time/lookback.py` | Freeze cases where local time is both behind and ahead of the UTC date. Positive days subtract exactly. Zero and negative days normalize to one. `window_start` and `lookback_since` agree. | Use `date.today()`, clamp nonpositive days to zero, apply `abs(days)`, or derive the date from a naive local datetime. |

For each row, the matching fault file is `tasks/<id>/fault/<canonical path relative to warehouse/>`. The matching explanation is `docs/solutions/<id>.md`, and wrong patches live in `tasks/<id>/mutants/`.

## Data structures

- `TaskWork` is `task id, category, owned paths, required invariants, mutant paths, source commit`.
- `EventScan` exposes named entity and time predicate operations plus collection, so tests can distinguish pushdown from post-filtering.
- `FirstLoadState` holds ordered rows and seen event ids across chunks, so a new chunk cannot recreate a frozen empty basis.
- `WindowState` holds event-id keyed facts, event-time bounds, processing completeness, and the declared lateness threshold.
- `MutantCase` is `stable filename id, changed paths, invariant it violates, strict-apply result, pytest result`.
- `TaskReceipt` is `task id, worker SHA, collected node ids, targeted audit digest, category review`.
- `IntegrationReceipt` is `task id, source SHA, integration SHA, full-audit digest, pushed head SHA`.

Store receipts in CI and pull-request output. Do not create a second task registry or hand-maintained result file.

## Subagent execution

- Complete and push the three API-redesign units first. The coordinator owns their shared `catalog.py` and prompt snapshot integration.
- Then use up to 15 concurrent task-hardening worktrees from the recorded redesign head. One worktree owns one task.
- The maximum per category is five incremental workers, four serving workers, three schema workers, two time workers, and one concurrency worker. These counts cover all 15 tasks after the three shared API shapes settle.
- Each worker owns only `tasks/<id>/tests/**`, `tasks/<id>/tests_adjudication/**`, `tasks/<id>/mutants/**`, `docs/solutions/<id>.md`, and that task's canonical and fault production files named in the table.
- The coordinator alone owns `contracts.py`, `catalog.py`, `patches.py`, `scripts/audit_tasks.py`, `verify.py`, `run_providers.py`, `prompt_bundle.py`, `README.md`, `docs/HARNESS.md`, `docs/TAXONOMY.md`, prompt snapshots, and plan files.
- Use at most five read-only category reviewers after task work finishes. They compare invariants across their category but do not edit worker branches.
- Keep one integration writer. Cherry-pick task commits in `catalog.all_ids()` order and run the full audit after every cherry-pick.
- If a shared audit defect appears, stop integration. The coordinator fixes it in a separate shared-infrastructure commit, reruns the full audit, and rebases unfinished worktrees. Never hide a shared fix inside a task commit.

## Verification

Static checks for each task:

- Collect `tasks/<id>/tests` and `tasks/<id>/tests_adjudication` twice and compare each tier's ordered node ids.
- Run `python -m compileall -q` on the task's canonical and fault production files.
- Run `git diff --name-only <redesign-head>...HEAD` and require every path to fit the worker's ownership list.
- Run `git diff --check`.

CLI runtime checks for each task:

- Use `control-cli` to run `python scripts/audit_tasks.py --task <id>`.
- Confirm the faulted checkout reaches pytest without an infrastructure error. Every mutant must apply strictly and produce pytest exit code 1. Confirm the generated gold diff applies strictly and passes.
- Inspect spy traces for bounded operations, write order, retry order, and forbidden calls where the task table requires them.

Integration checks:

- After every cherry-pick, run `python scripts/audit_tasks.py` across all 15 tasks. Do not integrate the next commit until it exits zero.
- After every third integrated task, run `python verify.py` from a clean clone and `python run_providers.py --check-prompts` with networking disabled.
- At the final head, run the full JSON audit twice and compare byte-for-byte output. Run all repository tests and `git diff --check`.

## Commit and push checkpoint

Each worker creates exactly one task commit. Do not combine task ids and do not amend a task after a later task integrates. The coordinator cherry-picks in catalog order, records the targeted and full-audit results, and pushes the public feature branch after every three green task commits. Push the final task immediately. Never push an integration head whose full audit is red.

## Exit criteria

- The public branch contains 15 reviewable task commits, one for each catalog id.
- Every invariant in the table has a direct public practice or adjudication test, and every named wrong answer has a strictly applicable registered mutant.
- The audit was green after each integrated task and is byte-for-byte deterministic at the final head.
- Gold stays green, faults stay red, and all known-wrong mutants produce test failures rather than grader or collection errors.
- The 12 non-redesigned prompt hashes remain unchanged. The three redesigned prompt hashes match their reviewed snapshots. Every official candidate message still omits tests, explanations, and mutants.
- The final green head and its verification results are pushed to the public repository.
