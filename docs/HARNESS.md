# OpenRouter harness for GLM 5.3 Flash

Locked so a score change is the host or the patch, not sampling.
Model slug `z-ai/glm-5.3-flash`. Thinking cannot be disabled.

| Setting | Value | Why |
|---|---|---|
| `temperature` | `0` | Repeatable host bake-off. |
| `max_tokens` | `131072` | Model max output. |
| `reasoning.effort` | `high` | Bake-off default. |
| `provider.only` | one host | No fallback. |
| `allow_fallbacks` | `false` | Same. |
| `require_parameters` | `true` | Official campaigns. |

Official candidate messages come from `harness/prompt_bundle.py`: incident,
entrypoint, editable paths, instructions, and faulted production
context. Tests and answers stay in the clone and never enter that
message. Shared instructions ask for one reasoning claim, then the
edit, then one unified diff, without naming tests, gold files, or
task mechanisms. `python run_providers.py --check-prompts` reprints
SHA-256 digests. Changing that sentence is a new prompt campaign.

Hop-trace fail modes (`logic_trace.cot_fail_mode`) fold hop lists plus
trial quality. Tokens stay `pass`, `apply_fail`, `overthink`,
`short_wrong`, `no_response`. In prose: pass means shown tests and
hidden tests both succeeded; apply-fail means `git apply` rejected the
diff; overthink means a fail with 8 or more hops or the same opening
diagnosis restated three times (one-shot CoT cuts, not tool calls);
short-wrong means a short CoT that still missed the grade; no-reply
means no quality tag and no hops (HTTP 429 or stream drop), not
short-wrong. Gold solution text is not a classifier input.
`no_response` trials stay in n and fail-mode counts; hop and think
means skip them. Each trial row stores `fail_mode`. Bake-off request
bodies match except `provider.only`.

Bake-off apply unwraps markdown fences and prefers a diff/patch
fence or a body that starts with `diff --git` / `--- a/`. A leading
Python diagnosis fence is skipped. Trailing prose after the last
hunk line is stripped. `@@` headers are rewritten from unique
old-side file context, then `git apply --index --whitespace=error
-p1` with no fuzz. Host `_run_pair` rows keep `TRIAL_ROW_KEYS` in
`run_providers.py`. Nested OpenRouter usage is lifted onto the jsonl
(`reasoning_tokens`, `cached_tokens`, `cost_prompt`). Applied diffs
land at `logs/runs/<run_id>/patches/`. Shown-pass / held-fail is
`held_fail`. CoT uses `reasoning_details` xor `reasoning`, not both.

Stay at `-k 1` until that campaign is clean; then `-k 3`. Dirty trees
are marked `-dirty` and `comparable` is false. Compare only clean SHA
rows.

```sh
python run_providers.py --spend --variance -k 1 --providers z-ai,novita
python scripts/compare_trials.py logs/runs/<run_id>.jsonl
```

Stream reads abort after 45s with no new tokens (`stream stall`) or
240s wall (`stream wall`). Keepalives no longer keep a trial alive
for hours. Three infra failures in a row for one host (HTTP 429,
stall, stream drop) skip the rest of that host without more OpenRouter
calls. Resume an incomplete bake-off with
`--spend --continue-run <run_id>` — already-written pairs are skipped.

`logs/LAST_RUN.md` is the latest table. A copy is also written to
`logs/runs/<run_id>/LAST_RUN.md`. The jsonl for that run is rewritten
in catalog task order, then provider, then trial.

Official campaigns:

```sh
python run_providers.py --campaign campaigns/official-v1.json --plan
python run_providers.py --campaign campaigns/official-v1.json --preflight
python run_providers.py --campaign campaigns/official-v1.json --resume
python report.py --manifest campaigns/official-v1.json --trials results/official-v1/trials.jsonl --out reports/official-v1 --check
```

`--resume` regrades saved artifacts. `--spend` is required to call
OpenRouter. Compare published campaign rows only at the frozen
`benchmark_repo_sha`, `grader_source_sha`, and image digest.
