# OpenRouter harness for GLM 5.3 Flash

Locked for this gym so a score change is the host or the patch, not
sampling. Model slug `z-ai/glm-5.3-flash`. Thinking cannot be disabled.

| Setting | Value | Why |
|---|---|---|
| `temperature` | `0` | Repeatable host bake-off. Z.ai coding rec is `1.0`; do not also set `top_p`. |
| `max_tokens` | `131072` | Model max output. A 2500 cap ate reasoning and returned empty `content`. |
| `reasoning.effort` | `high` | Bake-off default. `max` ran ~6 min of CoT on `schema_infer`. |
| `provider.only` | one host | No fallback. |
| `allow_fallbacks` | `false` | Same. |

Do not send `top_p` with `temperature` (Z.ai: pick one). Do not send
`reasoning.max_tokens` (not a GLM knob). Prefer fp8 hosts.

To score the model's ceiling instead of host variance, set
`temperature` to `1.0` and still omit `top_p`.

Fixtures: `python scripts/setup_eval.py --seed 42`.

`--spend --smoke` is the e2e check: `timestamptz_cutoff` on `z-ai` and
`novita`. `--spend --golden` is the five-task ladder (`timestamptz_cutoff`,
`schema_infer`, `unique_probe`, `latest_pointer`, `watermark_poison`).
Pytest failures print the error line (not a blank FAIL).

`tasks/<id>/tests` are shown in the prompt. `tasks/<id>/tests_held` are
not. A PASS requires both. After apply, `quality.py` tags the tree
`gold` (byte-match fault files to the gold warehouse, no extra files),
`equivalent` (only those files changed), or `other`.

Apply is strict: `git apply --recount`, then `patch --fuzz=0`, then a
context hunk walk. After each strategy the changed `.py` files must
`ast.parse`. A smashed tree is reverted and scored `apply_fail`, not a
pytest FAIL. `--fuzz=3` is not used.

`--jobs` runs (task, host) pairs in parallel (default `min(8, n_pairs)`).
One in-flight request per host. HTTP 429 retries with backoff.
Each pair streams SSE: a line every ~2s with elapsed, phase (`wait` /
`think` / `patch`), think/patch char counts, and OpenRouter keepalives.
Rows append to `results.jsonl` and `logs/runs/<run_id>.jsonl` as they
finish. `logs/LAST_RUN.md` refreshes after each pair. Raw payloads stay
in `logs/raw-*.json`.
