# Phase 4. Public Docker grader

[Back to the overview](./overview.md)

## Goal

Run untrusted candidate code in one public, pinned Docker grader with no network or secrets and hard resource limits. The security claim is host containment, not secrecy from public tests or proof against deliberately test-aware code. Save provider responses before grading so anyone can regrade them offline at the recorded benchmark repository SHA, grader source SHA, and image digest.

## Dependencies

- Phases 1 through 3 are green and pushed. They provide versioned records, a full `benchmark_repo_sha`, deterministic prompts, `TaskSpec.editable_checkout_paths`, and the only patch boundary.
- Docker Server 29.1.3 is available on the execution host. Use Docker as the required isolation boundary. Do not add an `unshare` fallback.
- Run `/how` on `run_providers.py`, `contracts.py`, `patches.py`, and `verify.py` before splitting provider and grader responsibilities.

## Changes

- Add `grade.py` as the public offline CLI. It reads one saved response artifact, verifies the requested benchmark repository SHA, grader source SHA, and image digest, materializes one faulted task archive, starts the pinned grader image, and writes one `GradeReport`. It must not import provider code or read provider credentials.
- Add `sandbox.py` as the small Docker lifecycle adapter. Use direct `docker` subprocess calls. Do not add a plugin system, scheduler, queue, database, or cluster deployment.
- Add `grader.py` as the image entrypoint. It unpacks one validated task archive in bounded temporary storage, reads the response artifact, calls `patches.py`, runs the public tests, emits one bounded JSON report, and exits.
- Keep provider HTTP and SSE work in `run_providers.py`. Write a complete `ResponseArtifact` atomically before starting `grade.py` as a separate process with an explicit environment allowlist. Never copy `OPENROUTER_API_KEY`, `.env`, proxy variables, cloud credentials, SSH state, or the parent environment into the grader process or container.
- Store the exact candidate text and its SHA-256 in each response artifact. Include the task id, prompt hash, model settings, requested and served provider, generation id, usage, finish reason, and `benchmark_repo_sha`. Regrading reads this file only and makes no provider request.
- Add `docker/grader.Dockerfile`, `docker/grader-image.json`, and `.dockerignore`. Pin the Python base by immutable digest, install only `requirements.lock` with hash checking, run as a fixed non-root user, and label the image with the full `grader_source_sha` and environment digest.
- Keep `.git`, `.env`, logs, generated results, credentials, caches, `warehouse/`, `tasks/`, `solutions/`, and `docs/solutions/` out of the image context. The image contains only generic grader code and dependencies.
- Add a deterministic `TaskArchive` builder to `grade.py`. It packages one already-faulted checkout, that task's public tests, and the minimum validated task policy. It excludes the canonical gold source, explanations, mutants, other tasks, Git data, logs, and results.
- Create the stopped container with no host mounts or Docker socket, copy the task archive and response artifact into its private writable layer, then start it with a read-only root and bounded `tmpfs` work directories.
- Require `grade.py` to resolve the image through `docker/grader-image.json` and verify its digest and grader-source label before use. Reject mutable tags, missing labels, dirty comparable runs, SHA mismatches, and absent pinned images. The later commit that records the image digest does not change `grader_source_sha`.
- Use `--network=none`, a read-only root filesystem, bounded `tmpfs` mounts for work and temporary files, a non-root user, all capabilities dropped, `no-new-privileges`, Docker's default seccomp profile, a private PID namespace, and no extra devices.
- Set fixed limits for CPU, memory and swap, PIDs, open files, file size, temporary-storage bytes and inodes, wall time, and combined standard output and error. Stream output through a byte counter. On timeout or output overflow, kill and remove the named container, then emit the matching stable reason code.
- Disable persistent container logging. Inspect exit state and OOM state before removal. Always remove the container and its temporary data after success, failure, interruption, or malformed output.
- Disable pytest plugin autoload and pass exact pre-collected node ids to pytest. Keep the outer grader supervisor responsible for process exit, resource state, bounded output, and final protocol encoding. Reject missing nodes, collection drift, duplicate protocol records, and malformed final reports as grader failures rather than passes.
- Document that candidate code can inspect its public tests at runtime and may execute shells, child processes, or dynamic libraries within the container. Docker isolation must contain those actions and enforce resource limits. The benchmark does not claim adversarial score integrity against a patch written to subvert pytest itself.
- Extend `GradeReport` and `TrialOutcome` in `contracts.py` with the image digest, applied patch hash, bounded output hash, test counts, and stable sandbox reasons. Keep provider failures, patch failures, public-test failures, timeouts, output limits, OOM kills, PID exhaustion, and grader infrastructure failures distinct.
- Update `verify.py` to invoke the same `grader.py` logic for public red and gold checks. Do not keep a second patch, seed, or pytest implementation.
- Add `tests/test_grade_cli.py` and `tests/test_sandbox.py`. Add malicious fixtures under `tests/probes/` for network access, secret discovery, host-file and cross-trial access, Docker-socket access, read-only writes, capability use, shell and child-process execution, dynamic-library loading, collection tricks, memory growth, file and process floods, an infinite loop, and output flooding.
- Update `README.md` and `docs/HARNESS.md` with image setup, offline regrading, recorded SHA requirements, resource limits, and the public threat model.

## Data structures

- `ResponseArtifact` is `schema version, trial and task ids, exact candidate text and hash, prompt hash, model and provider metadata, usage, finish reason, benchmark_repo_sha`.
- `TaskArchive` is `task id, benchmark_repo_sha, exact faulted checkout, public tests, task policy, content hash`.
- `GraderImageLock` is `immutable image reference and digest, grader_source_sha, environment digest, Dockerfile hash, supported platform`.
- `SandboxLimits` is `CPU quota, memory and swap bytes, PID and file limits, tmpfs bytes and inodes, wall seconds, output bytes`.
- `SandboxReport` is `container id, image digest, exit and OOM state, duration, output hash, applied patch hash, test counts, terminal reason`.

## Subagent execution

- Give one isolated worktree exclusive ownership of `grader.py`, its in-image tests, and the Docker files.
- In parallel, give a second worktree exclusive ownership of `sandbox.py`, `tests/test_sandbox.py`, and `tests/probes/**`.
- After those contracts settle, give a third worktree exclusive ownership of `grade.py`, response-artifact tests, and `tests/test_grade_cli.py`.
- The lead alone integrates `contracts.py`, `run_providers.py`, `verify.py`, `README.md`, and `docs/HARNESS.md`. Only the lead writes `docker/grader-image.json` after building from a pushed grader commit.
- Keep each worker on a separate branch and temporary Docker image name. The lead reviews and cherry-picks each green commit in dependency order.
- Treat artifact protocol, isolation probes, and image publication as three separate green integration checkpoints.

## Verification

Static checks:

- Run `python -m compileall -q contracts.py patches.py grader.py sandbox.py grade.py run_providers.py verify.py`.
- Run `python -m pytest -q tests/test_grade_cli.py tests/test_sandbox.py` plus all earlier contract, prompt, and patch tests.
- Inspect `.dockerignore` and the built image filesystem. Require no `.env`, credential, Git metadata, logs, results, caches, task corpus, canonical gold tree, tests, mutants, or solution material.
- Run `git diff --check` and verify that provider imports do not appear in `grade.py`, `grader.py`, or `sandbox.py`.

CLI runtime checks:

- Use `control-cli` to confirm Docker Server 29.1.3, build the image from the pinned base, inspect its digest and labels, and compare them with `docker/grader-image.json`.
- Run `python grade.py --response <saved-response>` twice with provider access disabled. Require the same patch hash, changed paths, test counts, terminal reason, `benchmark_repo_sha`, `grader_source_sha`, and image digest.
- Inspect the generated task archive. Require exactly one faulted checkout and its public tests, with no canonical gold file, explanation, mutant, unrelated task, Git metadata, log, or result.
- Set sentinel provider and cloud secrets in the host environment, then grade the secret probe. Confirm no sentinel appears in the report, output, container inspection, or image history.
- Run the network probe against DNS, a public address, and the metadata-service address. Require every outbound attempt to fail while the grader still returns a valid bounded report.
- Run the filesystem, cross-trial, Docker-socket, dynamic-library, and capability probes. Confirm the host sentinel remains unchanged, no host or neighboring-trial path or socket is visible, the root filesystem rejects writes, and privileged operations stay contained.
- Run the shell, child-process, dynamic-library, process-flood, file-flood, memory, infinite-loop, and output-flood probes. Confirm all activity remains inside the container, all children die with it, resource outcomes stay distinct, captured output never exceeds its limit, and no container remains.
- Run `conftest.py`, pytest-plugin, `sitecustomize`, import-path, early-exit, and malformed-report probes. Confirm denied file additions fail at the patch boundary and supervisor-observed protocol failures remain distinct from ordinary test failures.
- Run `python verify.py` from a clean clone through the same pinned image. Require all 15 public faults red, all public gold answers green, and the benchmark repository SHA, grader source SHA, and image digest in every report.

## Commit and push checkpoint

Run `/deslop` before every commit. Push the grader and sandbox implementation with all malicious-probe evidence first. Build the official image from that pushed full grader SHA, publish it at the immutable digest, then commit and push `docker/grader-image.json`. Do not begin Phase 5 until a clean clone can pull or build the pinned image and reproduce the checks.

## Exit criteria

- Provider requests finish and persist their exact responses before any untrusted code runs.
- `grade.py` regrades a saved response with no provider network call, provider key, private repository, or private grader.
- Candidate code can see its faulted checkout and public tests at runtime, but no canonical gold source, explanation, mutant, or unrelated task.
- Documentation makes no claim that Docker hides public tests at runtime or prevents deliberately test-aware candidate behavior.
- Every comparable report contains the exact `benchmark_repo_sha`, `grader_source_sha`, environment digest, and immutable image digest.
- The grader has no network, secrets, host mounts, extra capabilities, or unbounded CPU, memory, PIDs, time, temporary storage, files, or output.
- Malicious probes cannot reach the network, read host secrets, change host files, access Docker, retain a process, escape resource limits, or evade cleanup.
- Anyone can clone the public repository, obtain the pinned public image, and run the official grader.
