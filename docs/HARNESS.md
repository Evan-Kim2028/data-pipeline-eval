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

Pinned grader environment: `.python-version` and `requirements.lock`.
Comparable rows copy `benchmark_repo_sha` and `environment_sha256` from
the campaign manifest. Dirty trees are marked `-dirty` and are not
comparable.

Official candidate messages are built by `prompt_bundle.py` from the
incident file, declared entrypoint, editable paths, and faulted
production context. Tests and solutions stay in the clone but never
enter that message. `python run_providers.py --check-prompts` reprints
SHA-256 digests. Updating `tests/snapshots/prompt-sha256.json` requires
reviewing the rendered bytes.

`tasks/<id>/tests` and `tasks/<id>/tests_held` are public. Official
candidate messages omit both. A PASS currently requires both suites.
After apply, `quality.py` tags the tree
`gold` (byte-match fault files to the gold warehouse, no extra files),
`equivalent` (only those files changed), or `other`.

Candidate responses must contain one unified diff (`diff --git` or
`--- a/` / `+++ b/`). A markdown fence around that diff is unwrapped,
then apply is `git apply --index --whitespace=error -p1` onto allowed
paths. Format, policy, and apply failures are distinct. Empty fences
and non-diffs still fail format.
`python verify.py --check-patch TASK RESPONSE` checks a patch without
running candidate code.

Offline regrade is `python grade.py --response <artifact.json>`. The
CLI writes a `ResponseArtifact` before any candidate code runs, then
starts the pinned image from `docker/grader-image.json`. The container
uses `--network=none`, a read-only root, bounded tmpfs, dropped
capabilities, and a non-root user. Public tests are visible inside the
container; Docker does not hide them. Resource limits, not secrecy,
are the security claim.

`--jobs` runs (task, host) pairs in parallel (default `min(8, n_pairs)`).
One in-flight request per host. HTTP 429 retries with backoff.
Each pair streams SSE: a line every ~2s with elapsed, phase (`wait` /
`think` / `patch`), think/patch char counts, and OpenRouter keepalives.
Rows append to `results.jsonl` and `logs/runs/<run_id>.jsonl` as they
finish. `logs/LAST_RUN.md` refreshes after each pair. Raw payloads stay
in `logs/raw-*.json`.
