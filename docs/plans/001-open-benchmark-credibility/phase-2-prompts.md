# Phase 2: Deterministic candidate prompts

[Back to the overview](./overview.md)

## Goal

Build the exact public candidate message from explicit task metadata. Every task must provide enough production context to diagnose the incident without receiving tests or solutions. The builder hashes the same bytes sent to the model.

## Dependencies

- Phase 1 has landed its validated `TaskSpec`, revision fields, environment lock, and serialization contracts.
- `catalog.py` remains the only task registry. Public tests and solutions stay in this repository, but never enter an official candidate message.
- Run `/how` before changing the unfamiliar prompt, checkout, or provider request path.

## Changes

- Add `prompt_bundle.py` as the pure prompt builder. It accepts one validated `TaskSpec` and its materialized `TaskCheckout`, then returns canonical UTF-8 bytes with LF endings, one terminal newline, fixed section labels, the declared entrypoint, disclosed editable paths, and faulted context files in declared order.
- Use only `TaskSpec.context_checkout_paths` resolved against `TaskCheckout`. Remove filesystem-wide trees, sibling discovery, recursive globs, canonical repository reads, and ambient checkout state from candidate-message construction.
- Audit all 15 records in `catalog.py`. Each record needs one explicit import entrypoint, explicit editable checkout paths, and the smallest ordered production context that contains the fault overlay, the entrypoint definition, and the local collaborators needed to reason about the symptom.
- Rewrite every `tasks/*/prompt.txt` as an organic incident report. State observed inputs, behavior, timing, and user or operator impact. Do not name tests, assertions, hidden checks, solutions, gold behavior, the exact fixing function, or the required implementation. Put the shared checkout and unified-diff instructions in the renderer once.
- Update `run_providers.py` to send the renderer's exact decoded bytes and record their SHA-256 in the campaign manifest and trial row before the request. Tests remain available only to the public grading step after a candidate patch exists.
- Add a no-network `--render-prompt TASK` path and an all-task `--check-prompts` path to `run_providers.py`. Both use the same builder as paid runs.
- Add `tests/test_prompt_bundles.py` for canonical encoding, deterministic order, exact-byte hashing, path safety, entrypoint coverage, all-task rendering, and exclusion of `tests/`, `solutions/`, `.git/`, bytecode, pytest caches, virtual environments, logs, and generated results.
- Add `tests/snapshots/prompt-sha256.json` with the schema version, byte length, and exact digest for all 15 rendered messages. Snapshot updates require an explicit command and review.
- Update `docs/HARNESS.md` with the public prompt contract, snapshot update procedure, and the distinction between public availability and candidate-message inclusion.

For each task, compare the declared context against its public fault overlay and gold production tree. The candidate message must include every faulted production file and enough production call-chain context to reach it from the entrypoint. This review proves context coverage without copying test language into the prompt.

## Data structures

- `PromptBundle` is `task_id, checkout digest, entrypoint, ordered context paths, disclosed editable paths, exact content bytes, sha256`.
- `PromptSnapshot` is `schema_version, generated_by, tasks keyed by id with byte_length and sha256`.

The rendered bytes are authoritative. API payload text, snapshots, manifests, and trial records all derive from that one value.

## Subagent execution

- Give one isolated worktree exclusive ownership of `prompt_bundle.py`, the prompt CLI wiring in `run_providers.py`, and `tests/test_prompt_bundles.py`.
- In parallel, give a second worktree exclusive ownership of the 15 `catalog.py` context and entrypoint records plus catalog tests.
- Split the 15 `tasks/*/prompt.txt` files across three or more worktrees by task id. Prompt writers receive production and incident files only. They do not inspect tests or solutions while drafting.
- The lead integrates the disjoint commits, runs the `unslop` skill over prompt prose, and owns `tests/snapshots/prompt-sha256.json` and `docs/HARNESS.md` after all prompt bytes settle.
- Keep one writer per file and one branch per worktree. Rebase before integration, rerun the owned checks, and push each merged green task group to `feature/open-benchmark-credibility`.

## Verification

Static checks:

- Run `python -m compileall -q prompt_bundle.py catalog.py run_providers.py`.
- Run `python -m pytest -q tests/test_prompt_bundles.py` and the Phase 1 catalog and contract tests.
- Run the snapshot check and require exactly 15 task ids with no unreviewed digest changes.
- Run `git diff --check`.

CLI runtime checks:

- Use `control-cli` to run `python run_providers.py --check-prompts` in two clean clones at different absolute paths. Their task order, byte lengths, and hashes must match.
- Use `control-cli` to render representative calibration and very-hard tasks. Inspect the captured candidate messages for the declared entrypoint, editable paths, and faulted production context, with no denied path, canonical gold source, or test and solution content.
- Use `control-cli` to render all 15 tasks with network access disabled. Confirm the command makes no provider request and every printed digest matches the committed snapshot.
- Run `python verify.py` once more. Public starter and gold grading must remain red and green respectively for all 15 tasks.

## Commit and push checkpoint

Run `/deslop` before every commit. Commit prompt infrastructure, disjoint prompt groups, and the final reviewed snapshot as separate green checkpoints. Push each checkpoint to `feature/open-benchmark-credibility`; never push a snapshot that does not match the renderer.

## Exit criteria

- All 15 official candidate messages render deterministically from `catalog.py`.
- Every message identifies an entrypoint and contains enough production context to cover its fault path without test-derived instructions.
- No candidate message contains tests, solutions, repository internals, caches, logs, or generated results.
- The stored hash is over the exact bytes sent to the model and matches the reviewed snapshot.
- The public grader still passes from a clean clone, and prompt verification requires no network or private repository.
