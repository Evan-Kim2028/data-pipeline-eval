# Phase 8: Reporting and public release

[Back to the overview](./overview.md)

## Goal

Turn one frozen campaign into a deterministic report that shows uncertainty, failures, latency, and cost without manufacturing a winner. Publish the benchmark, grader, campaign evidence, and report from this repository under one public tag.

## Dependencies

- Phase 7 has pushed a frozen `campaigns/official-v1.json` and complete immutable artifacts under `results/official-v1/`.
- Every scored row names the public full benchmark repository SHA, grader source SHA, immutable grader image digest, manifest hash, prompt hash, requested provider, served provider, replicate, seed, outcome, latency, and cost state.
- The release uses no private grader, private tests, private answers, or private metadata service.

## Changes

- Add `report_stats.py` with pure standard-library calculations. Define end-to-end rate as passes over all planned trials. Define conditional repair rate as passes over trials with a valid applied patch and a terminal public-test verdict.
- Compute the failure decomposition from terminal outcome reasons. Show denominator and missing-value counts beside every rate, latency, and cost statistic.
- Produce task and category tables. Keep calibration tasks visible as their own suite and include them in the declared overall denominator.
- Use a fixed analysis seed and 10,000 task-level bootstrap samples. Form 95 percent intervals from percentile bounds. Resample task ids and retain every provider, seed, and replicate row for each sampled task. State that these intervals measure sensitivity to this 15-task corpus, not uncertainty over every possible code-repair task or model population.
- Pair providers only on matching task, prompt hash, replicate, and seed. Compare end-to-end outcomes on every complete pair. Report each provider's conditional repair rate independently. If a paired conditional difference is included, restrict it to pairs where both providers produced a valid applied patch and label that narrower estimand explicitly.
- Report median and interquartile range for latency and settled cost. Use the standard-library inclusive quartile definition. Do not impute missing values or treat an unpriced request as zero cost.
- Report the minimum detectable absolute effect for each paired comparison at two-sided alpha 0.05 and power 0.80. Use 10,000 deterministic simulations over paired task clusters and state the observed discordance and assumptions.
- Add `report.py` as a standard-library-only CLI. It validates the locked manifest and trial stream, writes deterministic `report.json`, `report.md`, `difficulty.json`, and `checksums.txt`, and supports `--check` without rewriting files.
- Keep provider order from the manifest. Do not emit ranks, winner labels, or tie-break scores. Label a paired difference inconclusive when its interval includes zero.
- Define empirical task difficulty as one minus that task's end-to-end success rate. Tie it to `campaign_id`, manifest hash, provider set, and report method. Keep the design estimate in `catalog.py`; do not replace it with a campaign result.
- Add `tests/test_report_stats.py`, `tests/test_report_cli.py`, and small frozen campaign fixtures that cover denominator rules, task clustering, pairing, missing values, deterministic output, and malformed inputs.
- Update `README.md`, `docs/HARNESS.md`, and `docs/TAXONOMY.md`. State that tests and answers are public but omitted from official candidate messages. Document clone, grade, campaign replay, report replay, frozen SHA comparison, and release commands.
- Add `scripts/check_release.py` to verify a fresh anonymous clone, the pinned environment and grader image, public `grade.py` execution, prompt exclusion, campaign and report replay, artifact checksums, and the proposed tag.

## Data structures

- `AnalysisConfig` is `campaign id, manifest hash, analysis seed, bootstrap samples, MDE simulations, confidence level, power, alpha, pairing keys, quartile method`.
- `RateSummary` is `numerator, denominator, rate, lower interval, upper interval, excluded count`.
- `ProviderSummary` is `requested provider, served-provider counts, end-to-end rate, conditional repair rate, failure counts, latency median and quartiles, cost median and quartiles`.
- `PairedDifference` is `provider pair, metric, complete pairs, missing pairs, estimate, interval, discordance, minimum detectable effect`.
- `TaskDifficulty` is `campaign id, manifest hash, task id, suite, provider set, planned trials, end-to-end rate, interval`.
- `ReleaseBundle` is `tag, release commit, benchmark repository SHA, grader source SHA, grader image digest, manifest hash, report method version, artifact paths and SHA-256 values`.

## Subagent execution

- The coordinator runs `/how` on the Phase 7 contracts and artifacts. Before any contested denominator, interval, artifact, tag, or disclosure choice is frozen, run `/interrogate` and record the lead verdict through `show-me-your-work`.
- Freeze `AnalysisConfig` and output schemas. Then fan out isolated worktrees with exclusive ownership of `report_stats.py`, `report.py`, their separate tests, documentation, and `scripts/check_release.py`.
- Give the statistics verifier a different model family and only frozen fixtures. It recomputes hand-checkable rates, paired differences, quartiles, and one small bootstrap case independently.
- Workers commit locally and never push. The coordinator integrates one green fan-out wave at a time, reruns all project checks, runs `/deslop`, commits, and pushes.
- Keep generated report artifacts under one coordinator-owned `reports/official-v1/` directory. No worker writes the release tag or GitHub release.

## Verification

Static checks:

- Run `python -m compileall -q report_stats.py report.py scripts/check_release.py`.
- Run `python -m pytest -q tests/test_report_stats.py tests/test_report_cli.py` and all earlier project tests.
- Confirm `report.py` imports only the Python standard library. Run `git diff --check`.

CLI runtime checks:

- Use `control-cli` to run report help, invalid-input, generate, and `--check` paths. Invalid hashes, duplicate trials, incomplete campaigns, and provider mismatches without the matching explicit outcome must produce stable nonzero exits.
- Generate the report twice in clean directories. Require byte-identical JSON, Markdown, difficulty data, and checksums.
- Compare fixture rates and paired differences by hand. Confirm infrastructure failures lower end-to-end rates but do not enter the conditional denominator.
- Run `python scripts/check_release.py --manifest campaigns/official-v1.json --report reports/official-v1 --tag benchmark-v1.0.0` against an anonymous clean clone.
- Regrade sampled saved `ResponseArtifact` files with `grade.py` at the manifest benchmark repository SHA, grader source SHA, and image digest. Require their grade reports and outcome classes to match the published rows.

## Commit and push checkpoint

The coordinator alone pushes. Push the green statistics and report-tool wave, then the documentation and clean-clone wave. Generate and verify official report artifacts in a final release-content commit and push it to `feature/open-benchmark-credibility`.

Run `/deslop` before every commit. Run `git push -u origin feature/open-benchmark-credibility`, open one ready GitHub PR with `gh pr create`, then verify it with `gh pr view`. After the PR exists, run the pstack Babysit playbook in `drive` mode until the exact head SHA is `READY`. Do not merge without explicit merge authority.

After the PR merges, rerun `scripts/check_release.py` on the exact public `main` SHA. Stop for separate explicit authority before creating or pushing the annotated tag. Stop again for separate explicit authority before creating the GitHub release. Once authorized, create `benchmark-v1.0.0` on the verified SHA, push the tag, and create the release with `gh release create benchmark-v1.0.0 --verify-tag`. Attach the locked manifest, trial and spend streams, response artifacts, report files, and checksums. Do not move or recreate the tag.

## Exit criteria

- A clean public clone at the pinned benchmark repository SHA, grader source SHA, and image digest runs the official grader and reproduces the report with no private input.
- The report contains both rates, outcome decomposition, task and category tables, task-level intervals, paired differences, latency and cost quartiles, minimum detectable effects, and campaign-bound difficulty.
- Every number exposes its denominator. Missing, infrastructure, provider mismatch, and unknown-cost rows remain visible.
- Provider order is stable and the report has no forced ranking.
- `README.md` and `docs/HARNESS.md` explain public tests and answers, candidate-message exclusion, frozen SHA comparison, replay, and release use.
- The ready PR is babysat at its exact head, and the immutable public tag and GitHub release point to the verified merge commit.
