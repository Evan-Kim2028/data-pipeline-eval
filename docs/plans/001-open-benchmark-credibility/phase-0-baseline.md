# Phase 0: Preserve and publish the current corpus

[Back to the overview](./overview.md)

## Goal

Turn the current dirty working tree into a reviewable, verified checkpoint without losing in-flight grader work or mixing local artifacts into the public repository. Establish the public feature branch that every later worktree uses. Public `main` at `e9de709` already contains all 15 tasks.

## Dependencies

- Begin in the primary `/home/evan/Documents/data-pipeline-eval` worktree.
- Do not reset, discard, or overwrite existing changes.
- The coordinator owns this phase. Do not fan out writers until the baseline is pushed.

## Changes

- Inspect the complete status and diff. The live planning baseline has tracked edits in `README.md`, `catalog.py`, `docs/HARNESS.md`, `run_providers.py`, and `verify.py`, plus untracked plan files, `quality.py`, and 15 `tasks/*/tests_held/` suites. Recheck this inventory because concurrent work may move it again.
- Create `feature/open-benchmark-credibility` from the current `main` head while preserving the working tree.
- Commit this plan as a documentation-only checkpoint.
- Review the in-flight harness, `quality.py`, and held-test changes against this plan. Commit them as a clearly named checkpoint only after the current verifier passes and a second reviewer confirms they contain no local artifacts. Later phases may replace them rather than preserve temporary interfaces.
- Treat `tests_held` as a temporary name. Phase 1 defines the final public practice and adjudication test paths, and Phase 5 migrates the files. Do not describe public files as hidden.
- Update `.gitignore` only when a local artifact is not already excluded. Never stage `.env`, raw responses, private notes, or credentials.
- Push the feature branch after both commits pass their checks.

## Data structures

- `BaselineReceipt` is `starting HEAD, plan commit, in-flight checkpoint commit, included paths, excluded paths, verification commands, pushed branch SHA`.

Keep the receipt in the decision trail required by `show-me-your-work`. Do not add a second state file.

## Subagent execution

- One read-only subagent reviews the intended staged plan diff.
- A second read-only subagent reviews the intended staged corpus diff for secrets, generated files, and accidental private content.
- The coordinator alone stages, commits, and pushes. No worker writes the branch during this phase.
- After the push, create all later subagent worktrees from the exact public baseline SHA.

## Verification

Static checks:

- Run `git diff --check`.
- Run `python -m compileall -q catalog.py verify.py run_providers.py scripts warehouse tasks`.
- Run `python verify.py` and require all 15 starters red and all 15 gold implementations green.
- Inspect staged files and require no `.env`, `internal/`, logs, results, caches, bytecode, raw responses, or ignored generated fixtures.

CLI runtime checks:

- Use `control-cli` to run fixture setup twice with seed 42 in separate temporary copies and compare generated hashes.
- Clone the pushed feature branch into a temporary directory and run the public setup and verifier from tracked files only.
- Confirm the clone reports exactly 15 catalog tasks.

## Commit and push checkpoint

Run `/deslop` on the documentation commit and all prose. Run the repository secret check before the corpus commit. Push with `git push -u origin feature/open-benchmark-credibility`. Record the public branch SHA in the decision trail.

## Exit criteria

- The plan and reviewed in-flight grader checkpoint exist on the public feature branch as separate commits.
- The primary worktree is clean except for explicitly documented local artifacts.
- A fresh clone of the pushed branch reconstructs fixtures and verifies all 15 tasks.
- Every later worktree starts from the recorded baseline SHA.
