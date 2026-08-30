# Open benchmark credibility plan

## Context

`data-pipeline-eval` has a useful core design. A canonical `warehouse/` tree becomes a broken checkout through one task fault overlay, and pytest decides whether a candidate repair restores the intended behavior. The current implementation weakens that design. Candidate messages include the grading tests, several tests accept plausible wrong repairs, copied solutions drift from the canonical gold, patch application is permissive, untrusted code runs with host access, and two recorded trials cannot support provider comparisons.

This plan turns the repository into one fully public, self-graded benchmark. Anyone can inspect the tests and answers, run the official grader, fork the tasks, and publish results. Official candidate messages omit tests and answers to keep the evaluated context consistent. This is a protocol rule, not a secrecy claim.

## Scope

Included:

- Preserve and review the current in-flight public grader work before redesign work. Public `main` already contains all 15 tasks.
- Keep one public repository for tasks, tests, answers, runner, grader, manifests, and reports.
- Make candidate prompts deterministic and useful without embedding tests.
- Make patch application strict and task-scoped.
- Grade untrusted code in a pinned Docker image with no secrets or network.
- Keep `warehouse/` as the only executable gold.
- Strengthen every task with direct invariants and known-wrong patches.
- Add replayable campaigns, honest uncertainty, periodic commits, public pushes, a PR, and an immutable release.
- Organize implementation for high subagent concurrency with disjoint worktrees and coordinator-owned integration.

Explicitly excluded:

- A private grader repository or hidden-test service.
- Claims that public tests are hidden or contamination-proof.
- Production-incident provenance work.
- New tasks before the existing 15 pass the hardened audit.
- Tool-using repository agents, multi-file repair tasks, LLM judges, leaderboards, databases, queues, Kubernetes, and a generic plugin framework.
- Forced provider rankings when the observed data cannot separate them.

## Constraints

- The public fault-overlay architecture stays. It is the strongest part of the repository.
- `catalog.py` remains the task metadata source. Do not add 15 per-task manifests.
- Official tasks allow edits only to declared existing production files. The shared candidate instruction must disclose those allowed paths.
- Public tests and solution prose remain available to humans but never enter an official rendered candidate message.
- Comparable results require the same benchmark repository SHA, grader source SHA, prompt hash, campaign manifest, and grader image digest.
- Provider calls remain opt-in through `--spend`.
- The coordinator is the only writer to the integration branch, shared result directories, tags, releases, and GitHub.
- No force pushes. Do not merge or create a release without explicit authority.

## Alternatives

### One public repository

Chosen. It gives every user the same inspectable grader and answer set. Frozen hashes make results auditable. Public availability may create future model contamination, so reports must identify model and repository dates and avoid secrecy claims.

### Two public repositories

Rejected. Separating public tasks and public tests adds synchronization work without hiding anything or improving reproducibility.

### Public corpus with a private grader

Rejected for this project. It prevents every user from independently reproducing the official score and conflicts with the open-benchmark goal.

## Target design

The benchmark has five enforced boundaries:

1. `catalog.py` defines each task, its entrypoint, candidate context, editable files, public practice and adjudication tests, canonical gold, explanation, and mutant directory.
2. `prompt_bundle.py` renders exact candidate bytes from validated task metadata. It cannot discover or include tests, answers, Git metadata, caches, logs, or results.
3. `patches.py` accepts one strict unified diff and modifies only declared existing source files.
4. `grade.py` replays a saved provider response through a pinned Docker grader. The container has no provider credentials, network, host mounts, or unbounded resources.
5. Campaign and report tools consume immutable JSONL records. They never infer missing identities or collapse provider, patch, sandbox, and test failures into one boolean.

Core records:

- `TaskSpec` names the complete public task contract and keeps repository paths distinct from candidate-checkout paths.
- `TaskCheckout` is the exact faulted file set consumed by prompts, patches, grading archives, and audits.
- `PromptBundle` contains the exact bytes and hash sent to a provider.
- `ResponseArtifact` preserves provider output before candidate code runs.
- `TrialOutcome` gives each terminal state one stable machine-readable reason.
- `TrialRecord` joins task, prompt, provider, response, grade, timing, usage, and cost facts.
- `CampaignManifest` freezes the trial matrix and environment.
- `GradeReport` records patch, sandbox, and pytest evidence.

## Phases

1. [Phase 0: Preserve and publish the current corpus](./phase-0-baseline.md)
2. [Phase 1: Contracts and reproducible metadata](./phase-1-contracts.md)
3. [Phase 2: Deterministic candidate prompts](./phase-2-prompts.md)
4. [Phase 3: Strict patch boundary](./phase-3-patch-boundary.md)
5. [Phase 4: Public Docker grader](./phase-4-sandbox.md)
6. [Phase 5: Audit answers and keep one gold tree](./phase-5-answer-audit.md)
7. [Phase 6: Harden every task](./phase-6-task-hardening.md)
8. [Phase 7: Reproducible campaigns](./phase-7-campaigns.md)
9. [Phase 8: Reporting and public release](./phase-8-reporting-release.md)

Project-wide verification lives in [testing.md](./testing.md).

## Parallel implementation

The coordinator first completes Phase 0 and Phase 1. Shared record shapes must settle before fan-out.

After Phase 1:

- One lane owns Phase 2 prompt rendering.
- One lane may prototype Phase 4 Docker commands and malicious probes without changing shared files.
- The coordinator keeps `contracts.py`, `catalog.py`, and integration files single-writer.

After Phase 2:

- Phase 3 patch work runs in one worktree.
- Phase 4 sandbox workers split Docker entrypoint, Docker lifecycle, and offline grade CLI into disjoint worktrees.

After Phase 5:

- The coordinator first lands and pushes Phase 7's shared contract additions.
- Phase 6 first lands three sequential API redesigns for `entity_reload`, `frozen_basis`, and `late_event_close`. It then creates one worktree per task, up to 15 concurrent task writers. Each owns only that task's two public test tiers, mutants, explanation, canonical file, and fault file.
- Category reviewers run read-only after task writers finish.
- Phase 7 campaign modules may develop in parallel from the same pushed shared-contract head because they own disjoint files. The official manifest and campaign cannot freeze until every Phase 6 task commit is integrated.

After Phase 7:

- Phase 8 splits statistics, report CLI, documentation, and clean-clone checks into separate worktrees.
- A different-model verifier recomputes the statistics from frozen fixtures.

Workers commit locally and never push. The coordinator reviews each diff, cherry-picks one green unit, reruns the combined checks, and pushes the integration branch. This removes shared branch and result-file races while retaining maximum code-writing concurrency.

## Commit and push cadence

- Phase 0 pushes the plan and current corpus baseline as separate commits.
- Phases 1 through 5 push after every green phase or independent green slice.
- Phase 6 pushes after every three integrated task commits and after the final task.
- Phase 7 pushes runner changes, the SHA-pinned manifest, and verified campaign artifacts separately.
- Phase 8 pushes report code, documentation and clean-clone checks, then release artifacts.
- The coordinator opens one ready PR after the final feature-branch push and uses the Babysit playbook until the exact head is ready.
- After an authorized merge, the coordinator verifies the public `main` commit. Tag creation and push require separate explicit authority. GitHub release creation requires another explicit authority.

Every commit must do one logical thing, pass its phase checks, pass `git diff --check`, and contain no credentials or local artifacts. Every push must point to a full audit-green integration SHA.

## Verification

Each phase has static and CLI checks. The full program must also pass [testing.md](./testing.md) from an anonymous clean clone. The required proof includes:

- All 15 faults fail by behavioral assertions in both public test tiers.
- All canonical gold repairs apply strictly and pass.
- Every registered known-wrong patch applies strictly and fails the invariant it violates.
- Candidate prompt bytes and hashes reproduce across clone paths.
- Malicious candidate probes cannot read secrets, use the network, change host files, survive cleanup, or exhaust unbounded resources.
- Saved responses regrade offline to the same outcome at the recorded benchmark repository SHA, grader source SHA, and image digest.
- Interrupted campaigns resume without duplicate trials or hidden spend.
- Reports regenerate byte for byte and expose every denominator, missing value, and failure class.

## Implementation guidance

- Run the `how` skill before changing each unfamiliar subsystem.
- Use `interrogate` before freezing contested sandbox, denominator, interval, artifact, or release decisions.
- Run `/deslop` before every commit and `unslop` over prompts, explanations, and documentation.
- Use `control-cli` for real command-line refusal, failure, interruption, resume, replay, and success paths.
- Keep a committed append-only [`audit.tsv`](./audit.tsv) through the `show-me-your-work` skill. Record decisions, integrated commits, verification evidence, pushes, and reversions.
- Use `babysit` after opening the PR.
- Prefer deletion over compatibility code. Remove the fuzzy patcher and duplicate solution tree instead of wrapping them.
- Do not advance after a red phase. Fix or revert the smallest failed unit, rerun its check, then continue.

## Definition of done

- One public repository contains all benchmark code, tasks, tests, canonical answers, explanations, manifests, replay artifacts, and reports.
- Anyone can clone a pinned public SHA and run the official grader without provider credentials.
- Official candidate messages omit tests and answers while disclosing their allowed edit paths.
- All 15 tasks pass deterministic fault, gold, and mutant audits.
- Untrusted grading uses the pinned Docker image and passes every malicious probe.
- One frozen campaign completes without unresolved trials or spend and reports uncertainty without a forced ranking.
- The final report reproduces from tracked artifacts.
- All implementation commits and periodic pushes are visible on the public feature branch.
- The verified merge commit owns the immutable public tag and GitHub release.

## Historical phase log

[`audit.tsv`](./audit.tsv) is the working log from building this public benchmark (phases 0–8). It records decisions, integrated commits, and verification evidence. It is not a second product, not a grader input, and not part of the task corpus. Official tasks, tests, and campaign artifacts live in the repository root.
