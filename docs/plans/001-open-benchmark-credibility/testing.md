# Project testing and release acceptance

[Back to the overview](./overview.md)

## Goal

Prove the public benchmark from tracked files, real CLI paths, sandbox attacks, campaign replay, and an anonymous clean clone. Tests alone are not sufficient verification. Each phase needs static checks, controlled CLI runs, and evidence tied to the pushed head SHA.

## Dependencies

- Use the pinned CPython patch from `.python-version`. Install the grader environment with `python -m pip install --require-hashes -r requirements.lock`.
- Run publishable checks from a clean worktree at the exact feature-branch or release SHA.
- Allow anonymous Git and Docker fetches only for clean-clone setup. Keep the grader network-disabled, and keep report replay offline. Provider preflight and `--spend` smoke runs are separate opt-in checks.

## Execution rules

- Start each unfamiliar phase with `/how`. Keep the cross-phase decisions and check receipts in the append-only trail required by `show-me-your-work`.
- Run `/interrogate` before freezing a contested release denominator, statistical method, provider disclosure, artifact set, or tag. Record the lead verdict and the evidence.
- Run `/deslop` before every commit and `/no-comments` before review. Use `control-cli` for CLI help, refusal, failure, interrupt, resume, and success paths.
- Give every write worker an isolated worktree and exclusive paths. Give runtime lanes separate temporary directories. Workers never push.
- The coordinator alone integrates, commits, tags, creates releases, and pushes after a green phase or fan-out wave.

## Project static checks

- Run `python -m compileall -q catalog.py contracts.py prompt_bundle.py patches.py grader.py sandbox.py grade.py run_providers.py campaign_plan.py trial_store.py report_stats.py report.py scripts warehouse tests`.
- Run `python -m pytest -q tests`.
- Run `python run_providers.py --check-prompts` with networking disabled. Require the committed hashes for all 15 tasks.
- Run `python scripts/audit_tasks.py --format json` twice and compare the output byte for byte.
- Run `git diff --check` and reject tracked bytecode, pytest caches, generated local logs, credentials, or absolute temporary paths.

## CLI runtime checks

- Use `control-cli` to run `python verify.py --validate-catalog`. Require 15 valid tasks and exit zero.
- Use `control-cli` to run `python verify.py`. Require every fault red by assertion, every generated public gold patch green, and every registered mutant red by assertion.
- Run `python scripts/setup_eval.py --seed 42` in two clean temporary clones. Compare every generated fixture hash.
- Exercise `grade.py --response` with saved artifacts that contain a valid gold diff, a no-op diff, an invalid diff, and a disallowed-path diff. Require distinct stable JSON outcomes and exit codes.
- Exercise `run_providers.py` with no spend flag, prompt rendering, campaign planning, preflight fixtures, interrupted fixture execution, resume, and a low spend cap.
- Exercise `report.py` with help, malformed input, generation, and `--check`. Generate twice and compare every report artifact byte for byte.

## Malicious sandbox probes

Run the focused sandbox suite with `python -m pytest -q tests/test_sandbox.py`. It must cover:

- Relative traversal, absolute paths, symlink escape, hard-link escape, and writes outside the candidate checkout.
- Patches to tests, grader code, prompt snapshots, public answers, catalog metadata, and files outside the task's allowed production paths.
- Reads of the host environment, `.env`, provider credentials, home directory, parent checkout, process information, and temporary files from another trial.
- Network sockets, DNS, subprocesses, shell execution, dynamic library loading, and attempts to start child or detached processes. Shells and libraries may run only inside the container; the test proves containment and cleanup, not prohibition.
- CPU, wall-time, memory, file-count, file-size, and output floods. Require deterministic timeout or resource outcomes and cleanup of every process and temporary directory.
- `conftest.py`, pytest-plugin, `sitecustomize`, import-path, and collection tricks that skip, replace, or forge test results.

A containment probe that triggers a supervisor-observed resource or protocol failure must produce an explicit sandbox or infrastructure outcome. It must never appear as an ordinary public-test failure, pass, or zero-cost skipped row. Deliberately test-aware candidate behavior is outside the Docker security claim and remains a limitation of an open, pytest-graded benchmark.

## Audit-task checks

- Require one `TaskSpec` for each of the 15 `tasks/*` directories, stable catalog order, known category and suite, and one resolvable production entrypoint.
- Require nonempty public practice and adjudication suites, one fault overlay, one canonical gold mapping into `warehouse/`, one prose explanation under `docs/solutions/`, and at least one strictly applicable mutant for every task.
- Collect each public test tier twice. Treat no tests, import failure, timeout, and collection failure as audit infrastructure errors.
- Require faulted starters to exit 1 through assertion failures in both public tiers. Require generated gold diffs to apply with the declared strip level, zero fuzz, allowed paths only, byte-match the canonical gold, and pass both tiers.
- Require every mutant to apply strictly and fail the invariant it names. Do not count patch, collection, import, or sandbox failure as mutant rejection.
- Inspect all rendered candidate messages. They may contain only the task incident, declared entrypoint, and declared production context. Public tests, explanations, mutants, gold files, caches, logs, and results stay out.

## Campaign and replay checks

- Expand `campaigns/official-v1.json` twice. Compare manifest hash, trial ids, prompt hashes, replicate and seed pairing, calibration membership, and rotated provider order.
- Validate capability snapshots and require `require_parameters` set to `true`. A missing capability or requested and served provider mismatch stays explicit and cannot trigger fallback.
- Kill a fixture campaign after each durable boundary. Resume it twice and require one terminal row per trial id, no rewritten row, and no silent replay of unresolved billed work.
- Reconcile reserved, settled, released, and unknown spend. Block dispatch before the cap can be exceeded, including concurrent reservations.
- Regrade a sample from each outcome class with `grade.py --response` at the recorded benchmark repository SHA, grader source SHA, and image digest. Compare artifact hashes, grade reports, and outcome mapping.
- Generate the report from the frozen rows twice. Check end-to-end and conditional denominators, failure totals, paired keys, bootstrap seed, latency and cost missing counts, minimum detectable effects, and campaign-bound difficulty.

## Clean-clone checks

- Run `python scripts/check_release.py --manifest campaigns/official-v1.json --report reports/official-v1 --tag benchmark-v1.0.0`.
- Make the script clone `https://github.com/Evan-Kim2028/data-pipeline-eval.git` anonymously into a new temporary directory. Check out the full pinned SHA and use only tracked files.
- Recreate the pinned environment, validate the catalog, rebuild fixtures, verify the grader image digest, run the full task audit, render prompt hashes, regrade saved response artifacts, regenerate the report, and verify checksums.
- Keep network access off for grader and report replay. Run provider preflight and one paid calibration smoke as separate opt-in checks with a fresh low spend cap.
- Repeat the release check by tag and by full commit SHA. Both checkouts must identify the same immutable release commit and benchmark inputs.

## Release acceptance criteria

- The public repository is the only source for benchmark code, grader code, both public test tiers, answers, manifests, and report inputs.
- Anyone can clone the pinned SHA, obtain the public pinned image, install the locked environment, and run the official grader. After setup, grading needs no provider credentials and report replay needs no network.
- Official candidate messages omit tests and answers. The clone still exposes every public test, canonical gold file, explanation, and registered mutant.
- Every official trial records the full public benchmark repository SHA, grader source SHA, immutable grader image digest, manifest and prompt hashes, task, suite, replicate, seed, requested and served provider, explicit outcome, artifact hashes, latency, usage, and cost state.
- The official campaign has no duplicate, truncated, missing, or unresolved trial. Artifact checksums and sampled regrades match.
- The report exposes denominators, failure decomposition, task and category tables, task-level intervals, paired differences, median and interquartile latency and cost, minimum detectable effects, and campaign-bound difficulty. It contains no rank or winner field.
- The ready PR is green and babysat at its exact head SHA. The immutable `benchmark-v1.0.0` tag and GitHub release point to the verified merge commit.

## Subagent execution

- Fan out static, sandbox, task-audit, campaign-replay, report-math, and clean-clone lanes where their outputs do not share a file or result directory.
- Each lane reports the exact head SHA, commands, exit codes, and artifact paths. A different-model verifier checks statistics, sandbox boundaries, and release evidence.
- The coordinator aggregates receipts, fixes ownership conflicts before integration, and reruns the full project checks after every fan-out wave.

## Commit and push cadence

- Push the verified Phase 0 plan and corpus baseline commits before creating implementation worktrees.
- Push each green Phase 1 through Phase 5 checkpoint before the next phase starts.
- In Phase 6, push after every three green task commits and after the final task.
- In Phase 7, push the runner wave, the SHA-pinned manifest, and the verified official campaign artifacts as separate commits.
- In Phase 8, push the report wave, the documentation and clean-clone wave, and the verified release-content commit.
- After the final push, open one ready PR. Run the pstack Babysit playbook in `drive` mode until the exact head SHA is `READY`. Tag and create the public release only after the authorized merge and one final clean-clone check.
