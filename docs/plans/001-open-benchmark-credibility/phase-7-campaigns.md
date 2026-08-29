# Phase 7: Reproducible campaigns

[Back to the overview](./overview.md)

## Goal

Run a declared set of public tasks, providers, seeds, and replicates from one frozen manifest. Preserve every requested trial and its spend as append-only evidence. A resumed run must schedule only missing work and must never hide provider substitution or infrastructure failure as a repair failure.

## Dependencies

- Phases 1 through 5 are green and pushed before campaign tooling starts. They provide `contracts.py`, `prompt_bundle.py`, `grade.py`, the pinned Docker grader, provider response artifacts, a full public `benchmark_repo_sha`, `grader_source_sha`, and an immutable grader image digest. Phase 6 may run in parallel, but the official manifest cannot freeze or spend until every hardened task commit is integrated and pushed.
- `catalog.py` remains the task source. The official campaign includes both `default` and `calibration` tasks.
- The pinned repository SHA contains the runner, grader, public tests, and public answers. Official candidate messages still contain only the incident prompt and declared production context.

## Changes

- Add `campaign_plan.py` to load and validate manifests, expand deterministic `TrialSpec` values, pair one prompt and seed across providers, and rotate the starting provider by catalog index plus replicate index modulo provider count.
- Add `trial_store.py` as the single writer for campaign rows and spend events. Model each trial as planned, reserved, dispatched, response_saved, graded, or terminal. Append, flush, and fsync each transition before the next external action. Reject illegal transitions, duplicate terminal trial ids, mixed manifest hashes, truncated rows, and changes to a frozen manifest.
- Extend the provider HTTP and SSE path in `run_providers.py` with capability preflight. Record supported parameters and pricing, set `require_parameters` to `true`, disable fallback, and keep `requested_provider` separate from `served_provider`.
- Make `run_providers.py` load campaigns through `campaign_plan.py` and persist them through `trial_store.py`. Add `--campaign`, `--plan`, `--preflight`, `--resume`, and the existing explicit `--spend` gate. Build candidate messages only through `prompt_bundle.py`, save each `ResponseArtifact`, then invoke the public `grade.py` process.
- Add `campaigns/official-v1.json`. Pin the public repository URL, full benchmark repository SHA, grader source SHA, grader image digest, ordered task ids, calibration inclusion, model parameters, requested providers, replicate count, paired seeds, deterministic order rule, concurrency, zero automatic completion retries, spend cap, and analysis seed.
- Write official artifacts under `results/official-v1/`. Store `manifest.lock.json`, `preflight.jsonl`, `trials.jsonl`, `spend.jsonl`, and content-addressed `ResponseArtifact` files. Keep ad hoc `logs/` and the legacy root `results.jsonl` outside publishable inputs.
- Extend `contracts.py` so every terminal `TrialOutcome` has a stable reason code. Cover pass, public-test failure, invalid patch, sandbox rejection, provider error, timeout, empty response, parameter rejection, capability unavailable, requested and served provider mismatch, budget exhaustion, and interrupted unknown spend.
- Require preflight pricing before dispatch. The single coordinator must append and fsync a conservative per-trial reservation before each request, then settle it from provider usage after the response artifact is durably saved. Resume regrades an existing response artifact without another provider request. Preserve unknown billed spend after interruption and require explicit reconciliation before retrying any unresolved dispatch.
- Add focused tests in `tests/test_campaign_plan.py`, `tests/test_trial_store.py`, and `tests/test_run_providers.py`.

## Data structures

- `CampaignManifest` is `schema_version, campaign_id, repository_url, benchmark_repo_sha, grader_source_sha, grader_image_digest, environment_sha256, ordered tasks, calibration tasks, model parameters, requested providers, require_parameters, replicates, paired seeds, order rule, jobs, retry policy, spend cap, analysis seed`.
- `ProviderCapability` is `requested provider, endpoint id, supported parameters, pricing, context limit, preflight time, availability, response digest`.
- `TrialSpec` is `trial_id, campaign id, task id, suite, replicate, seed, prompt hash, requested provider, order position, manifest hash`.
- `TrialRecord` is `TrialSpec fields, served provider, generation id, artifact hashes, timing, usage, cost, grade report, outcome class, outcome reason`.
- `SpendEvent` is `event id, trial id, reserve | settle | release | unknown, amount, currency, provider generation id, timestamp`.
- `TrialState` is `planned | reserved | dispatched | response_saved | graded | terminal` with explicit legal transitions.

## Subagent execution

- The coordinator runs `/how` on `contracts.py`, `run_providers.py`, and the public grader before assigning work. Keep the campaign decision trail in the append-only file required by `show-me-your-work`.
- Land and push any Phase 7 additions to `contracts.py` before starting campaign workers. Then fan out isolated worktrees with exclusive ownership of `campaign_plan.py`, `trial_store.py`, and their matching test files.
- After those commits pass their owned tests, assign one integration worktree exclusive ownership of `run_providers.py` and `tests/test_run_providers.py`. Assign `campaigns/official-v1.json` to a separate manifest owner.
- Workers commit only to their worktree branches and never push. The coordinator inspects each diff, cherry-picks one green wave at a time, reruns the combined checks, runs `/deslop`, commits, and pushes.
- Give runtime lanes separate temporary result directories. Only the coordinator may write `results/official-v1/`.

## Verification

Static checks:

- Run `python -m compileall -q contracts.py campaign_plan.py trial_store.py run_providers.py grade.py`.
- Run `python -m pytest -q tests/test_campaign_plan.py tests/test_trial_store.py tests/test_run_providers.py tests/test_grade_cli.py`.
- Run the earlier contract, prompt, grader, and sandbox tests. Run `git diff --check`.

CLI runtime checks:

- Use `control-cli` to render the same campaign plan twice. Require byte-identical trial ids, prompt hashes, paired seeds, and rotated provider positions.
- Run fixture-backed preflight cases for full support, a missing parameter, a missing provider, and a served-provider mismatch. No case may silently fall back.
- Interrupt a fixture campaign after completed rows and during one reserved request. Resume it twice. Completed trial ids must not repeat, missing trials must finish once, and unresolved spend must stay explicit.
- Run a concurrent fixture campaign against a low spend cap. The sum of settled, reserved, and unknown spend must never exceed the dispatch limit.
- Run one opt-in live calibration smoke only after preflight and `--spend`. Regrade its saved `ResponseArtifact` with `grade.py` at the manifest SHAs and compare the grade report.

## Commit and push checkpoint

The coordinator alone pushes. Push a green runner and test commit first, then pin `campaigns/official-v1.json` to that public full SHA and push the manifest commit. After the official campaign completes, verify and push the immutable result artifacts in a separate commit. Run `/deslop` before each commit. Never start or publish a campaign from an unpushed SHA.

## Exit criteria

- One public manifest reproduces the ordered trial plan, including calibration tasks, replicates, paired seeds, and provider rotation.
- Every planned trial has one terminal row, and resume adds no duplicate terminal row. An unresolved interruption remains explicit and blocks official campaign finalization.
- Every request records both requested and served provider, and `require_parameters` is preflighted and sent.
- Spend reconciles to provider usage, with unknown billed spend visible and bounded.
- Candidate messages omit tests and answers, while the same public repository and frozen SHAs provide the official grader, tests, answers, and replay artifacts.
