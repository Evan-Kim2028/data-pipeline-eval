# Phase 1: Contracts and reproducible metadata

[Back to the overview](./overview.md)

## Goal

Define the public benchmark's typed records, validate the 15-task catalog at the repository boundary, and pin the grader environment. A published result must identify the exact repository commit and execution environment that produced it. This phase keeps `catalog.py` as the task metadata source. Do not replace it with 15 task TOML files.

## Dependencies

- The repository remains the only public benchmark and grader source. There is no private grader repository or hidden metadata service.
- Start from the clean, pushed Phase 0 baseline on `feature/open-benchmark-credibility`, and run `/how` before changing an unfamiliar catalog, result-writing, or grading path.
- Phase 2 consumes these contracts but Phase 1 does not depend on prompt-bundle work.

## Changes

- Add `contracts.py` with immutable, versioned records and strict JSON encoding and decoding. Define distinct repository-relative and candidate-checkout-relative path types. Reject unknown schema versions, missing comparison fields, invalid hashes, path-domain mixing, and contradictory outcomes when data crosses the file or CLI boundary.
- Keep all task records in `catalog.py`. Convert the current dictionaries to `TaskSpec` values while preserving `all_ids()` and `default_ids()` as derived views. Include repository paths for prompts, faults, both public test tiers, canonical gold, explanations, and mutants. Include checkout paths for candidate context and editable files plus one explicit import entrypoint per task.
- Add catalog validation in `catalog.py`. Require unique ids, known categories and suites, exactly one record for each `tasks/*` directory, existing repository paths, nonempty candidate context, resolvable faulted entrypoints, and no candidate path under tests, solutions, Git data, or cache directories.
- Add `checkouts.py` as the one deterministic materializer. It copies canonical production files, overlays the declared fault, and returns a `TaskCheckout` with exact checkout-relative file hashes. Prompt rendering, patch application, grading archives, and audits must consume this object rather than reconstructing paths independently.
- Add `.python-version` for the exact supported CPython patch and `requirements.lock` for every grader and test dependency with hashes. Treat those two committed files as the environment source of truth.
- Update `verify.py` with a catalog-only validation mode and fail before grading if the catalog or environment contract is invalid.
- Update `run_providers.py` to create one `CampaignManifest`, emit contract-shaped `TrialRecord` and `GradeReport` data, and copy the manifest's full `benchmark_repo_sha` and environment digest into each standalone trial row. Phase 4 adds the grader source SHA and immutable image digest. A publishable campaign must use clean commits. Dirty local runs remain clearly non-comparable.
- Add focused contract, catalog, serialization, revision, and environment tests under `tests/`. Use temporary git repositories for clean, dirty, missing-revision, and differing repo/grader revision cases.
- Update `README.md` and `docs/HARNESS.md` with the clean-environment setup, public metadata policy, and the rule that comparable rows require a full repository SHA and environment digest. Do not duplicate task metadata there.

## Data structures

- `RepoPath` is a validated repository-relative POSIX path that cannot be used as a candidate-checkout path.
- `CheckoutPath` is a validated candidate-root-relative POSIX path that cannot address repository-only files.
- `TaskSpec` is `id, category, estimated_difficulty, suite, one_liner, prompt_repo_path, fault_repo_path, practice_tests_repo_path, adjudication_tests_repo_path, gold_repo_path, explanation_repo_path, mutant_repo_dir, context_checkout_paths, editable_checkout_paths, entrypoint`.
- `TaskCheckout` is `task id, benchmark_repo_sha, exact faulted file map, ordered file hashes, checkout digest`.
- `TrialOutcome` is a closed tagged value for provider failure, empty or malformed output, patch rejection, sandbox failure, timeout, test failure, pass, budget stop, or interrupted spend.
- `TrialRecord` is `schema_version, campaign_id, trial_id, task_id, model/provider settings, prompt_sha256, benchmark_repo_sha, environment_sha256, timing, usage, outcome, artifact paths`.
- `CampaignManifest` is `schema_version, campaign_id, created_at, ordered task ids, repetitions, concurrency, model/provider settings, benchmark_repo_sha, environment_sha256, prompt hashes`.
- `GradeReport` is `schema_version, trial_id, task_id, benchmark_repo_sha, command, exit_code, test counts, duration, output_sha256`.

`catalog.py` owns task metadata. `CampaignManifest` owns shared run metadata. Trial and grade records derive from those sources rather than rebuilding metadata from globals or filenames.

## Subagent execution

- Give one subagent an isolated worktree and exclusive ownership of `contracts.py`, `catalog.py`, and their tests.
- In parallel, give a second worktree exclusive ownership of `.python-version`, `requirements.lock`, and environment tests.
- After the contract commit lands, give a third worktree exclusive ownership of `checkouts.py` and its tests. Then give a fourth worktree exclusive ownership of `run_providers.py` result serialization. The lead alone integrates `verify.py`, `README.md`, and `docs/HARNESS.md`.
- Never assign two agents the same file or branch. Rebase each worktree on the public feature branch, verify its owned slice, then cherry-pick. Push each merged green slice so the public branch never depends on unpushed work.

## Verification

Static checks:

- Run `python -m compileall -q contracts.py catalog.py checkouts.py verify.py run_providers.py`.
- Run the focused contract, catalog, environment, and serialization tests with `python -m pytest -q tests`.
- Run `git diff --check`.
- Create a clean environment with the pinned Python and install `requirements.lock` with pip hash checking.

CLI runtime checks:

- Use `control-cli` to run `python verify.py --validate-catalog` from a clean clone. Confirm it reports all 15 tasks and exits zero.
- Use `control-cli` to run `python verify.py`. Confirm every starter is red, every public gold tree is green, and the process exits zero.
- Exercise a no-network campaign fixture and inspect its JSONL output. Every trial and grade report must contain the exact clean `benchmark_repo_sha` and environment digest from its manifest.

## Commit and push checkpoint

Run `/deslop` on every staged diff. Commit only after the static and CLI checks pass. Use small green commits for contracts and environment pinning, then result wiring. Push them to `feature/open-benchmark-credibility` before Phase 2 starts.

## Exit criteria

- All 15 tasks validate from `catalog.py`; no per-task metadata files exist.
- Contract round trips preserve every comparison field and reject invalid states.
- A clean clone recreates the pinned grader environment and passes the public verifier.
- Published trial rows cannot omit or silently infer `benchmark_repo_sha` or the environment digest.
- Phase 2 can build prompts using only validated `TaskSpec` values.
