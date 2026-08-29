# Phase 3. Strict patch boundary

[Back to the overview](./overview.md)

## Goal

Accept one exact unified-diff response, enforce each task's edit boundary, and apply the patch through one fixed `git apply` command. Invalid response syntax, denied edits, and clean patches that do not apply must produce distinct public outcomes.

## Dependencies

- Phase 1 has landed `contracts.py` and validated `TaskSpec` records in `catalog.py`.
- Phase 2 has landed `prompt_bundle.py` and tells candidates to return only a unified diff against the seeded checkout.
- Start from the pushed Phase 2 head. Run `/how` on `run_providers.py`, `verify.py`, and the new contract paths before moving patch or checkout behavior.

## Changes

- Add `patches.py` as the only response-validation and patch-application path. Accept UTF-8 bytes that contain one bare unified-diff document. Reject Markdown fences, prose, NUL bytes, empty patches, malformed headers, and incomplete hunks as format failures.
- Enforce the ordered `TaskSpec.editable_checkout_paths` defined in Phase 1. Each current task declares only its faulted production file. Phase 2 discloses the same paths in the candidate message.
- Parse every file header before invoking Git. Require matching `a/` and `b/` paths for an existing tracked regular file with one link. Reject absolute paths, `..` components, backslashes, control characters, symlink or hard-link targets, symlink ancestors, and symlink mode changes.
- Reject new files, deletions, renames, copies, binary patches, file mode changes, submodule changes, and every path with a `tests` component. Also deny `.git`, `solutions`, caches, logs, and generated-result paths even if a future task record lists one.
- Require the parsed changed-path set to be nonempty and a subset of `TaskSpec.editable_checkout_paths`. Reject duplicate file sections and conflicting operations on one path.
- Apply validated bytes once with `git apply --index --whitespace=error -p1`. Do not use `--recount`, `--unsafe-paths`, alternate strip levels, `patch`, fuzz, rejected hunks, or context replacement.
- Compare the staged name-status output with the validator's path set after application. Accept only modified regular files. Treat any extra, missing, untracked, deleted, or type-changed path as a policy failure and discard the temporary checkout.
- Delete `_extract_python_or_diff`, `_apply_context_hunks`, and `_apply_model_output` from `run_providers.py`. Route provider responses, `verify.py`, future audits, and fixture tests through `patches.py`.
- Add stable `invalid_patch_format`, `patch_policy_rejected`, and `patch_did_not_apply` reason codes to `contracts.py`. Keep bounded, path-relative diagnostics in the grade and trial records.
- Add `tests/test_patches.py` with valid multi-hunk fixtures plus malformed, traversal, absolute, symlink, hard-link, rename, copy, delete, binary, new-file, test-path, undeclared-path, duplicate-section, whitespace, and context-mismatch cases.
- Add a no-network `verify.py --check-patch TASK RESPONSE` path. It seeds a disposable checkout, reports the reason code and changed paths, and never runs candidate code.
- Update `docs/HARNESS.md` with the exact response grammar, editable-path rule, fixed strip level, and failure classes.

## Data structures

- `ValidatedPatch` is `sha256, exact bytes, ordered modified paths`.
- `PatchFailure` is `format | policy | apply, stable reason code, bounded relative diagnostic`.
- `PatchReport` is `task id, response sha256, status, changed paths, failure`.
- `TaskSpec.editable_checkout_paths` is an ordered tuple of exact `CheckoutPath` values.

## Subagent execution

- Give one isolated worktree exclusive ownership of `patches.py` and `tests/test_patches.py`.
- After its public shapes settle, give a second worktree exclusive ownership of outcome-code additions in `contracts.py` and their tests.
- The lead alone integrates `run_providers.py`, `verify.py`, `prompt_bundle.py`, `catalog.py`, prompt snapshots if the shared response instruction changes, and `docs/HARNESS.md`.
- Keep one owner per file. Rebase each worktree on the pushed Phase 2 head, review its diff, and cherry-pick one green commit at a time.

## Verification

Static checks:

- Run `python -m compileall -q patches.py contracts.py catalog.py run_providers.py verify.py`.
- Run `python -m pytest -q tests/test_patches.py` plus the Phase 1 contract and catalog tests and the Phase 2 prompt tests.
- Run `rg -n "_extract_python_or_diff|_apply_context_hunks|_apply_model_output|--fuzz|--recount|--unsafe-paths" run_providers.py patches.py` and require no matches.
- Run `git diff --check`.

CLI runtime checks:

- Use `control-cli` to run `python verify.py --check-patch timestamptz_cutoff <valid-response>`. Confirm one declared source file changes and the command exits zero.
- Run the same command with fenced prose, a stale hunk, a test edit, an undeclared source edit, traversal, a symlink, a hard link, a rename, a deletion, and a binary patch. Confirm the expected format, apply, or policy reason code and a nonzero exit.
- Run two clean disposable checkouts with the same valid response. Compare the changed path list, staged diff, patch hash, and report after removing temporary paths. They must match byte for byte.
- Run `python verify.py` to confirm all public starter and gold checks remain red and green for all 15 tasks.

## Commit and push checkpoint

Run `/deslop` on every staged diff. Commit the validator and adversarial tests first, then the task policy and caller migration. Push each green commit to `feature/open-benchmark-credibility` before Phase 4 starts. Do not carry the deleted fallback code in a compatibility module.

## Exit criteria

- Every candidate response reaches one strict validator and one fixed `git apply` route.
- No candidate can add, delete, rename, copy, replace, or edit a symlink, test, undeclared file, or path outside the checkout.
- Format, policy, and application failures have stable machine-readable outcomes.
- The same patch bytes and task revision produce the same changed files and report in fresh checkouts.
- `run_providers.py`, `verify.py`, audits, and the Phase 4 grader can only use the shared patch boundary.
