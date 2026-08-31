# OpenRouter harness for GLM 5.3 Flash

These settings stay fixed so a score change comes from the host or
the patch. The model slug is `z-ai/glm-5.3-flash`. Thinking stays
on.

| Setting | Value | Why |
|---|---|---|
| `temperature` | `0` | Repeatable request on one host. |
| `max_tokens` | `131072` | Model max output. |
| `reasoning.effort` | `high` | Default effort. |
| `provider.only` | one host | One listed host. |
| `allow_fallbacks` | `false` | Matches `provider.only`. |
| `require_parameters` | `true` | Official campaigns. |

Official candidate messages come from `harness/prompt_bundle.py`.
Each message includes the incident, entrypoint, editable paths,
instructions, and faulted production context. Shared instructions
ask for one reasoning claim, then the edit, then one unified diff.
They leave tests, gold files, and task mechanisms unnamed.
`python run_providers.py --check-prompts` reprints SHA-256 digests.
Changing that instruction sentence starts a new prompt campaign.

Hop-trace fail modes (`logic_trace.cot_fail_mode`) fold hop lists
plus trial quality. The tokens are `pass`, `apply_fail`,
`overthink`, `short_wrong`, and `no_response`. Pass means shown
tests and held tests both succeeded. Apply-fail means `git apply`
rejected the diff. Overthink means a fail with 8 or more hops, or
the same opening diagnosis restated three times. Short-wrong means
a short chain of thought that still missed the grade. No-reply
means no quality tag and no hops, which covers HTTP 429 and stream
drops. Gold solution text stays out of the classifier. `no_response`
trials stay in n and in fail-mode counts. Hop and think means skip
those rows. Each trial row stores `fail_mode`. Request bodies match
except `provider.only`.

Apply unwraps markdown fences and prefers a diff or patch fence, or
a body that starts with `diff --git` or `--- a/`. A leading Python
diagnosis fence is skipped. Trailing prose after the last hunk line
is stripped. `@@` headers are rewritten from unique old-side file
context, then `git apply --index --whitespace=error -p1` with no
fuzz. Host `_run_pair` rows keep `TRIAL_ROW_KEYS` in
`run_providers.py`. Nested OpenRouter usage is lifted onto the
jsonl (`reasoning_tokens`, `cached_tokens`, `cost_prompt`). Applied
diffs land at `logs/runs/<run_id>/patches/`. Shown-pass with
held-fail is `held_fail`. The runner stores one of
`reasoning_details` or `reasoning`.

Stay at `-k 1` until that campaign is clean, then `-k 3`. Dirty
trees are marked `-dirty` and `comparable` is false. Compare clean
SHA rows.

```sh
python run_providers.py --spend --variance -k 1 --providers z-ai,novita
python scripts/compare_trials.py logs/runs/<run_id>.jsonl
```

Stream reads abort after 45s with no new tokens (`stream stall`) or
240s wall (`stream wall`). Keepalives stop holding a trial open
for hours. Three infra failures in a row for one host (HTTP 429,
stall, stream drop) skip the rest of that host. Resume an
incomplete run with `--spend --continue-run <run_id>`.
Already-written pairs are skipped.

`logs/LAST_RUN.md` is the latest table. A copy is also written to
`logs/runs/<run_id>/LAST_RUN.md`. The jsonl for that run is
rewritten in catalog task order, then provider, then trial.

OpenRouter does not surface Fireworks prefix-cache hits. Call
`https://api.fireworks.ai/inference/v1/chat/completions` directly
with `accounts/fireworks/models/glm-5p3-flash`. Send the same
session id as JSON `prompt_cache_key` / `user` and as the
`x-session-affinity` header. Hits show up on
`fireworks-cached-prompt-tokens` and
`usage.prompt_tokens_details.cached_tokens`. Probe with
`FIREWORKS_API_KEY=... python scripts/probe_fireworks_cache.py`.

Official campaigns:

```sh
python run_providers.py --campaign campaigns/official-v1.json --plan
python run_providers.py --campaign campaigns/official-v1.json --preflight
python run_providers.py --campaign campaigns/official-v1.json --resume
python scripts/report.py --manifest campaigns/official-v1.json --trials results/official-v1/trials.jsonl --out reports/official-v1 --check
```

`--resume` grades a saved model response again. `--spend` is
required to call OpenRouter. Published campaign rows compare at
the same repo commit, grader commit, and Docker image.
